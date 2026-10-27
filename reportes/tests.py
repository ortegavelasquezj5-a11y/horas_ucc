"""Pruebas de las pantallas: permisos por rol y flujo completo de una hora."""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from actividades.models import Actividad, Inscripcion, TipoActividad
from horas.models import RegistroHoras
from usuarios.models import Programa, Usuario
from usuarios.tests import crear_usuario

Rol = Usuario.Rol


@override_settings(MEDIA_ROOT="/tmp/horas_ucc_test_media")
class VistasTests(TestCase):
    def setUp(self):
        self.sistemas = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        self.derecho = Programa.objects.create(nombre="Derecho", meta_horas=50)
        self.estudiante = crear_usuario(Rol.ESTUDIANTE, "E001", self.sistemas, 6)
        self.estudiante_derecho = crear_usuario(Rol.ESTUDIANTE, "E900", self.derecho, 9)
        self.lider = crear_usuario(Rol.LIDER, "L001")
        self.bienestar = crear_usuario(Rol.BIENESTAR, "B001")
        self.coordinador = crear_usuario(Rol.COORDINADOR, "C001", self.sistemas)
        self.admin = crear_usuario(Rol.ADMIN, "A001")
        self.tipo = TipoActividad.objects.create(nombre="Deportiva")

    def entrar(self, usuario):
        self.client.force_login(usuario)

    # Permisos por rol -------------------------------------------------------
    def test_cada_rol_llega_a_su_pantalla(self):
        esperado = {
            self.estudiante: reverse("horas:mis_horas"),
            self.lider: reverse("actividades:gestion"),
            self.bienestar: reverse("horas:aprobar"),
            self.coordinador: reverse("reportes:seguimiento"),
            self.admin: reverse("usuarios:lista"),
        }
        for usuario, url in esperado.items():
            self.entrar(usuario)
            self.assertRedirects(self.client.get(reverse("inicio")), url)

    def test_estudiante_no_entra_a_pantallas_de_otros_roles(self):
        self.entrar(self.estudiante)
        for nombre in ("horas:aprobar", "actividades:gestion", "usuarios:lista", "reportes:seguimiento"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)

    def test_lider_no_aprueba_horas(self):
        self.entrar(self.lider)
        self.assertEqual(self.client.get(reverse("horas:aprobar")).status_code, 403)

    # Flujo completo de una hora ---------------------------------------------
    def test_flujo_crear_inscribir_asistir_aprobar(self):
        # 1. El líder crea y publica la actividad
        self.entrar(self.lider)
        inicio = timezone.localtime() + timedelta(days=2)
        respuesta = self.client.post(reverse("actividades:crear"), {
            "nombre": "Torneo de voleibol", "tipo": self.tipo.pk, "lugar": "Coliseo",
            "fecha_inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
            "fecha_fin": (inicio + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
            "cupo": 20, "horas_otorga": "4", "descripcion": "", "accion": "publicar",
        })
        self.assertRedirects(respuesta, reverse("actividades:gestion"))
        actividad = Actividad.objects.get()
        self.assertEqual(actividad.estado, Actividad.Estado.PUBLICADA)

        # 2. El estudiante la ve y se inscribe
        self.entrar(self.estudiante)
        self.assertContains(self.client.get(reverse("actividades:catalogo")), "Torneo de voleibol")
        self.client.post(reverse("actividades:inscribir", args=[actividad.pk]))
        self.assertTrue(Inscripcion.objects.filter(estudiante=self.estudiante).exists())

        # 3. Pasa la fecha y el líder registra la asistencia
        Actividad.objects.filter(pk=actividad.pk).update(fecha_inicio=timezone.now() - timedelta(hours=4),
                                                         fecha_fin=timezone.now() - timedelta(hours=1))
        self.entrar(self.lider)
        self.client.post(reverse("actividades:asistencia", args=[actividad.pk]), {"presentes": [self.estudiante.pk]})
        registro = RegistroHoras.objects.get()
        self.assertEqual(registro.estado, RegistroHoras.Estado.POR_APROBAR)

        # 4. Bienestar aprueba
        self.entrar(self.bienestar)
        self.assertContains(self.client.get(reverse("horas:aprobar")), self.estudiante.nombre_completo)
        self.client.post(reverse("horas:revisar", args=[registro.pk]), {"accion": "aprobar", "horas": "4"})
        registro.refresh_from_db()
        self.assertEqual(registro.estado, RegistroHoras.Estado.APROBADA)

        # 5. El estudiante ve sus 4 horas y la notificación
        self.entrar(self.estudiante)
        respuesta = self.client.get(reverse("horas:mis_horas"))
        self.assertEqual(respuesta.context["resumen"]["aprobadas"], 4)
        self.assertContains(self.client.get(reverse("notificaciones:lista")), "aprobó 4 h")

    def test_rechazar_sin_motivo_muestra_error(self):
        registro = RegistroHoras.objects.create(
            estudiante=self.estudiante, nombre_actividad="Curso externo", tipo=self.tipo,
            fecha_actividad=timezone.localdate(), horas=5,
        )
        self.entrar(self.bienestar)
        respuesta = self.client.post(reverse("horas:revisar", args=[registro.pk]), {"accion": "rechazar", "motivo": ""}, follow=True)
        self.assertContains(respuesta, "motivo del rechazo")
        registro.refresh_from_db()
        self.assertEqual(registro.estado, RegistroHoras.Estado.POR_APROBAR)

    # Soportes ---------------------------------------------------------------
    def test_cargar_soporte_y_solo_dueno_o_bienestar_lo_ven(self):
        self.entrar(self.estudiante)
        archivo = SimpleUploadedFile("certificado.pdf", b"%PDF-1.4 prueba", content_type="application/pdf")
        respuesta = self.client.post(reverse("horas:soporte"), {
            "nombre_actividad": "Primeros auxilios", "tipo": self.tipo.pk,
            "fecha_actividad": (timezone.localdate() - timedelta(days=3)).isoformat(),
            "horas": "8", "soporte": archivo,
        })
        self.assertRedirects(respuesta, reverse("horas:soporte"))
        registro = RegistroHoras.objects.get()
        url = reverse("horas:ver_soporte", args=[registro.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.entrar(self.estudiante_derecho)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.entrar(self.bienestar)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_soporte_con_extension_invalida(self):
        self.entrar(self.estudiante)
        respuesta = self.client.post(reverse("horas:soporte"), {
            "nombre_actividad": "Curso", "tipo": self.tipo.pk,
            "fecha_actividad": timezone.localdate().isoformat(), "horas": "2",
            "soporte": SimpleUploadedFile("script.exe", b"MZ"),
        })
        self.assertContains(respuesta, "PDF, JPG o PNG")
        self.assertFalse(RegistroHoras.objects.exists())

    # Seguimiento ------------------------------------------------------------
    def test_coordinador_solo_ve_su_programa(self):
        self.entrar(self.coordinador)
        respuesta = self.client.get(reverse("reportes:seguimiento"))
        codigos = [f["estudiante"].codigo for f in respuesta.context["filas"]]
        self.assertEqual(codigos, ["E001"])

    def test_estudiante_de_semestre_alto_aparece_en_riesgo(self):
        self.entrar(self.bienestar)
        respuesta = self.client.get(reverse("reportes:seguimiento"), {"estado": "en-riesgo"})
        self.assertEqual([f["estudiante"].codigo for f in respuesta.context["filas"]], ["E900"])

    # CRUD de usuarios y actividades -----------------------------------------
    def test_admin_crea_usuario_y_valida_codigo_repetido(self):
        self.entrar(self.admin)
        datos = {
            "codigo": "u2026050", "nombres": "Luis", "apellidos": "Gómez", "correo": "Luis.Gomez@campusucc.edu.co",
            "rol": Rol.ESTUDIANTE, "programa": self.sistemas.pk, "semestre": 3, "clave": "Horas.UCC.2026",
        }
        self.assertRedirects(self.client.post(reverse("usuarios:crear"), datos), reverse("usuarios:lista"))
        nuevo = Usuario.objects.get(codigo="U2026050")
        self.assertEqual(nuevo.correo, "luis.gomez@campusucc.edu.co")
        self.assertTrue(nuevo.check_password("Horas.UCC.2026"))
        datos["correo"] = "otro@campusucc.edu.co"
        self.assertContains(self.client.post(reverse("usuarios:crear"), datos), "Ya existe un usuario con este código")

    def test_estudiante_sin_programa_no_se_crea(self):
        self.entrar(self.admin)
        respuesta = self.client.post(reverse("usuarios:crear"), {
            "codigo": "X1", "nombres": "A", "apellidos": "B", "correo": "x1@campusucc.edu.co",
            "rol": Rol.ESTUDIANTE, "clave": "Horas.UCC.2026",
        })
        self.assertContains(respuesta, "deben tener programa")

    def test_admin_desactiva_usuario(self):
        self.entrar(self.admin)
        self.client.post(reverse("usuarios:estado", args=[self.estudiante.pk]))
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.is_active)

    def test_actividad_con_fin_antes_del_inicio(self):
        self.entrar(self.lider)
        inicio = timezone.localtime() + timedelta(days=2)
        respuesta = self.client.post(reverse("actividades:crear"), {
            "nombre": "X", "tipo": self.tipo.pk, "lugar": "Aula 1",
            "fecha_inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
            "fecha_fin": (inicio - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "cupo": 5, "horas_otorga": "2", "accion": "guardar",
        })
        self.assertContains(respuesta, "no puede ser anterior")

    def test_lider_no_edita_actividad_de_otro_lider(self):
        otro = crear_usuario(Rol.LIDER, "L002")
        inicio = timezone.now() + timedelta(days=3)
        actividad = Actividad.objects.create(
            nombre="Ajena", tipo=self.tipo, responsable=otro, lugar="Aula", fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(hours=1), cupo=5, horas_otorga=2,
        )
        self.entrar(self.lider)
        self.assertEqual(self.client.get(reverse("actividades:editar", args=[actividad.pk])).status_code, 403)
