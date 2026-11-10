from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from horas.models import RegistroHoras
from notificaciones.models import Notificacion
from usuarios.models import Programa, Usuario
from usuarios.tests import crear_usuario

from . import services
from .models import Actividad, Inscripcion, TipoActividad

Rol = Usuario.Rol


def crear_actividad(responsable, dias=3, cupo=2, estado=Actividad.Estado.PUBLICADA, horas="4"):
    inicio = timezone.now() + timedelta(days=dias)
    return Actividad.objects.create(
        nombre="Torneo de fútbol sala", tipo=TipoActividad.objects.get_or_create(nombre="Deportiva")[0],
        responsable=responsable, lugar="Coliseo", fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(hours=3), cupo=cupo, horas_otorga=Decimal(horas), estado=estado,
    )


class BaseTests(TestCase):
    def setUp(self):
        self.programa = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        self.e1 = crear_usuario(Rol.ESTUDIANTE, "E001", self.programa, 6)
        self.e2 = crear_usuario(Rol.ESTUDIANTE, "E002", self.programa, 8)
        self.e3 = crear_usuario(Rol.ESTUDIANTE, "E003", self.programa, 2)
        self.lider = crear_usuario(Rol.LIDER, "L001")
        self.otro_lider = crear_usuario(Rol.LIDER, "L002")
        self.bienestar = crear_usuario(Rol.BIENESTAR, "B001")


class InscripcionTests(BaseTests):
    def test_inscripcion_exitosa(self):
        actividad = crear_actividad(self.lider)
        inscripcion = services.inscribir(self.e1, actividad)
        self.assertEqual(inscripcion.estado, Inscripcion.Estado.INSCRITO)

    def test_no_permite_inscribirse_dos_veces(self):
        actividad = crear_actividad(self.lider)
        services.inscribir(self.e1, actividad)
        with self.assertRaisesMessage(services.ReglaDeNegocioError, "Ya estás inscrito"):
            services.inscribir(self.e1, actividad)

    def test_no_permite_superar_el_cupo(self):
        actividad = crear_actividad(self.lider, cupo=2)
        services.inscribir(self.e1, actividad)
        services.inscribir(self.e2, actividad)
        with self.assertRaisesMessage(services.ReglaDeNegocioError, "no tiene cupos"):
            services.inscribir(self.e3, actividad)

    def test_cancelar_libera_el_cupo_y_se_puede_volver(self):
        actividad = crear_actividad(self.lider, cupo=1)
        inscripcion = services.inscribir(self.e1, actividad)
        services.cancelar_inscripcion(inscripcion, self.e1)
        services.inscribir(self.e2, actividad)
        self.assertEqual(actividad.cupos_disponibles, 0)

    def test_reinscribirse_reactiva_la_misma_fila(self):
        actividad = crear_actividad(self.lider)
        inscripcion = services.inscribir(self.e1, actividad)
        services.cancelar_inscripcion(inscripcion, self.e1)
        otra = services.inscribir(self.e1, actividad)
        self.assertEqual(otra.pk, inscripcion.pk)
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_no_se_inscribe_en_borrador(self):
        actividad = crear_actividad(self.lider, estado=Actividad.Estado.BORRADOR)
        with self.assertRaises(services.ReglaDeNegocioError):
            services.inscribir(self.e1, actividad)

    def test_no_se_inscribe_si_ya_empezo(self):
        actividad = crear_actividad(self.lider, dias=-1)
        with self.assertRaisesMessage(services.ReglaDeNegocioError, "ya empezó"):
            services.inscribir(self.e1, actividad)

    def test_solo_estudiantes_se_inscriben(self):
        actividad = crear_actividad(self.lider)
        with self.assertRaises(services.ReglaDeNegocioError):
            services.inscribir(self.lider, actividad)


class PublicarTests(BaseTests):
    def test_publicar_avisa_a_los_estudiantes(self):
        actividad = crear_actividad(self.lider, estado=Actividad.Estado.BORRADOR)
        services.publicar(actividad, self.lider)
        self.assertEqual(actividad.estado, Actividad.Estado.PUBLICADA)
        self.assertEqual(Notificacion.objects.filter(usuario__rol=Rol.ESTUDIANTE).count(), 3)

    def test_otro_lider_no_puede_publicar(self):
        actividad = crear_actividad(self.lider, estado=Actividad.Estado.BORRADOR)
        with self.assertRaises(services.ReglaDeNegocioError):
            services.publicar(actividad, self.otro_lider)

    def test_cancelar_actividad_avisa_a_los_inscritos(self):
        actividad = crear_actividad(self.lider)
        services.inscribir(self.e1, actividad)
        services.cancelar_actividad(actividad, self.lider)
        self.assertEqual(actividad.cupos_ocupados, 0)
        self.assertTrue(Notificacion.objects.filter(usuario=self.e1, mensaje__contains="cancelada").exists())


class AsistenciaTests(BaseTests):
    def _actividad_pasada_con_inscritos(self):
        actividad = crear_actividad(self.lider, dias=-1, cupo=5)
        for e in (self.e1, self.e2):
            Inscripcion.objects.create(estudiante=e, actividad=actividad)
        return actividad

    def test_asistencia_genera_horas_por_aprobar_solo_a_quien_asistio(self):
        actividad = self._actividad_pasada_con_inscritos()
        services.registrar_asistencia(actividad, self.lider, [self.e1.pk])
        self.assertEqual(RegistroHoras.objects.count(), 1)
        registro = RegistroHoras.objects.get()
        self.assertEqual(registro.estudiante, self.e1)
        self.assertEqual(registro.estado, RegistroHoras.Estado.POR_APROBAR)
        self.assertEqual(registro.horas, Decimal("4"))
        actividad.refresh_from_db()
        self.assertEqual(actividad.estado, Actividad.Estado.FINALIZADA)

    def test_corregir_asistencia_quita_horas_no_revisadas(self):
        actividad = self._actividad_pasada_con_inscritos()
        services.registrar_asistencia(actividad, self.lider, [self.e1.pk, self.e2.pk])
        services.registrar_asistencia(actividad, self.lider, [self.e1.pk])
        self.assertEqual(RegistroHoras.objects.count(), 1)

    def test_no_se_registra_asistencia_antes_de_la_actividad(self):
        actividad = crear_actividad(self.lider, dias=2)
        with self.assertRaisesMessage(services.ReglaDeNegocioError, "ya empezó"):
            services.registrar_asistencia(actividad, self.lider, [])

    def test_otro_lider_no_registra_asistencia(self):
        actividad = self._actividad_pasada_con_inscritos()
        with self.assertRaises(services.ReglaDeNegocioError):
            services.registrar_asistencia(actividad, self.otro_lider, [self.e1.pk])

    def test_bienestar_si_puede_registrar_asistencia(self):
        actividad = self._actividad_pasada_con_inscritos()
        services.registrar_asistencia(actividad, self.bienestar, [self.e2.pk])
        self.assertEqual(RegistroHoras.objects.get().estudiante, self.e2)


class FrontendAjaxTests(BaseTests):
    """Semana 4: búsqueda en vivo, inscripción con fetch y eliminación real."""

    FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}

    def test_busqueda_en_vivo_devuelve_solo_las_tarjetas(self):
        crear_actividad(self.lider)
        self.client.force_login(self.e1)
        respuesta = self.client.get("/actividades/?q=fútbol", **self.FETCH)
        self.assertContains(respuesta, "Torneo de fútbol sala")
        self.assertNotContains(respuesta, "<html")
        self.assertTemplateUsed(respuesta, "actividades/_tarjetas.html")

    def test_inscripcion_con_fetch_responde_json(self):
        actividad = crear_actividad(self.lider, cupo=1)
        self.client.force_login(self.e1)
        respuesta = self.client.post(f"/actividades/{actividad.pk}/inscribir/", **self.FETCH)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["ok"])
        self.client.force_login(self.e2)
        respuesta = self.client.post(f"/actividades/{actividad.pk}/inscribir/", **self.FETCH)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("cupos", respuesta.json()["mensaje"])

    def test_elimina_actividad_en_borrador(self):
        actividad = crear_actividad(self.lider, estado=Actividad.Estado.BORRADOR)
        self.client.force_login(self.lider)
        self.client.post(f"/actividades/{actividad.pk}/eliminar/")
        self.assertFalse(Actividad.objects.filter(pk=actividad.pk).exists())

    def test_no_elimina_actividad_publicada(self):
        actividad = crear_actividad(self.lider)
        self.client.force_login(self.lider)
        respuesta = self.client.post(f"/actividades/{actividad.pk}/eliminar/")
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Actividad.objects.filter(pk=actividad.pk).exists())

    def test_otro_lider_no_elimina(self):
        actividad = crear_actividad(self.lider, estado=Actividad.Estado.BORRADOR)
        self.client.force_login(self.otro_lider)
        self.assertEqual(self.client.post(f"/actividades/{actividad.pk}/eliminar/").status_code, 403)
