from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from actividades.models import TipoActividad
from actividades.services import ReglaDeNegocioError
from usuarios.models import Programa, Usuario
from usuarios.tests import crear_usuario

from . import services
from .models import RegistroHoras

Rol = Usuario.Rol


def pdf(nombre="certificado.pdf", tamano=1000):
    return SimpleUploadedFile(nombre, b"%PDF" + b"0" * tamano, content_type="application/pdf")


@override_settings(MEDIA_ROOT="/tmp/horas_ucc_test_media")
class HorasTests(TestCase):
    def setUp(self):
        self.programa = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        self.estudiante = crear_usuario(Rol.ESTUDIANTE, "E001", self.programa, 6)
        self.bienestar = crear_usuario(Rol.BIENESTAR, "B001")
        self.lider = crear_usuario(Rol.LIDER, "L001")
        self.tipo = TipoActividad.objects.create(nombre="Bienestar")
        self.ayer = timezone.localdate() - timedelta(days=1)

    def solicitud(self, horas="8", **kwargs):
        datos = dict(nombre_actividad="Primeros auxilios", tipo=self.tipo,
                     fecha_actividad=self.ayer, horas=horas, soporte=pdf())
        datos.update(kwargs)
        return services.solicitar_horas_externas(self.estudiante, **datos)

    # Soportes externos
    def test_solicitud_queda_por_aprobar(self):
        self.assertEqual(self.solicitud().estado, RegistroHoras.Estado.POR_APROBAR)

    def test_soporte_obligatorio(self):
        with self.assertRaisesMessage(ReglaDeNegocioError, "obligatorio"):
            self.solicitud(soporte=None)

    def test_soporte_con_extension_no_permitida(self):
        with self.assertRaisesMessage(ReglaDeNegocioError, "PDF, JPG o PNG"):
            self.solicitud(soporte=SimpleUploadedFile("virus.exe", b"x"))

    def test_soporte_de_mas_de_5_mb(self):
        with self.assertRaisesMessage(ReglaDeNegocioError, "5 MB"):
            self.solicitud(soporte=pdf(tamano=5 * 1024 * 1024 + 1))

    def test_horas_en_cero(self):
        with self.assertRaisesMessage(ReglaDeNegocioError, "mayores que 0"):
            self.solicitud(horas="0")

    def test_fecha_futura(self):
        with self.assertRaisesMessage(ReglaDeNegocioError, "futura"):
            self.solicitud(fecha_actividad=timezone.localdate() + timedelta(days=2))

    # Aprobación
    def test_aprobar_suma_al_acumulado(self):
        registro = self.solicitud(horas="8")
        services.aprobar(registro, self.bienestar)
        resumen = services.resumen_horas(self.estudiante)
        self.assertEqual(resumen["aprobadas"], Decimal("8"))
        self.assertEqual(resumen["faltan"], Decimal("52"))
        self.assertEqual(resumen["porcentaje"], 13)

    def test_por_aprobar_no_suma_al_acumulado(self):
        self.solicitud(horas="8")
        resumen = services.resumen_horas(self.estudiante)
        self.assertEqual(resumen["aprobadas"], Decimal("0"))
        self.assertEqual(resumen["por_aprobar"], Decimal("8"))

    def test_ajustar_horas_exige_motivo(self):
        registro = self.solicitud(horas="8")
        with self.assertRaisesMessage(ReglaDeNegocioError, "motivo del ajuste"):
            services.aprobar(registro, self.bienestar, horas="6")
        services.aprobar(registro, self.bienestar, horas="6", motivo="El certificado dice 6 h")
        registro.refresh_from_db()
        self.assertEqual(registro.horas, Decimal("6"))

    def test_rechazar_exige_motivo(self):
        registro = self.solicitud()
        with self.assertRaisesMessage(ReglaDeNegocioError, "motivo del rechazo"):
            services.rechazar(registro, self.bienestar, "  ")
        services.rechazar(registro, self.bienestar, "El soporte no tiene fecha")
        self.assertEqual(registro.estado, RegistroHoras.Estado.RECHAZADA)
        self.assertTrue(self.estudiante.notificaciones.filter(mensaje__contains="rechazada").exists())

    def test_no_se_revisa_dos_veces(self):
        registro = self.solicitud()
        services.aprobar(registro, self.bienestar)
        with self.assertRaisesMessage(ReglaDeNegocioError, "ya fue revisada"):
            services.rechazar(registro, self.bienestar, "otro motivo")

    def test_un_lider_no_puede_aprobar(self):
        registro = self.solicitud()
        with self.assertRaises(ReglaDeNegocioError):
            services.aprobar(registro, self.lider)

    # Seguimiento
    def test_estado_de_cumplimiento(self):
        self.assertEqual(services.estado_cumplimiento(Decimal("60"), 60, 5), "cumple")
        self.assertEqual(services.estado_cumplimiento(Decimal("30"), 60, 8), "en-riesgo")
        self.assertEqual(services.estado_cumplimiento(Decimal("30"), 60, 5), "en-progreso")

    def test_seguimiento_usa_una_sola_consulta(self):
        for i in range(2, 6):
            crear_usuario(Rol.ESTUDIANTE, f"E00{i}", self.programa, i)
        with self.assertNumQueries(1):
            filas = services.seguimiento(programa=self.programa)
        self.assertEqual(len(filas), 5)
