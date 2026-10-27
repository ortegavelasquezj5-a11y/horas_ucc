from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from actividades.models import Actividad, TipoActividad
from usuarios.models import Programa, Usuario
from usuarios.tests import crear_usuario

Rol = Usuario.Rol


class ApiTests(TestCase):
    def setUp(self):
        programa = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        self.estudiante = crear_usuario(Rol.ESTUDIANTE, "E001", programa, 6)
        self.lider = crear_usuario(Rol.LIDER, "L001")
        self.bienestar = crear_usuario(Rol.BIENESTAR, "B001")
        inicio = timezone.now() + timedelta(days=2)
        self.actividad = Actividad.objects.create(
            nombre="Club de lectura", tipo=TipoActividad.objects.create(nombre="Cultural"),
            responsable=self.lider, lugar="Biblioteca", fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(hours=2), cupo=1, horas_otorga=2,
            estado=Actividad.Estado.PUBLICADA,
        )

    def test_sin_sesion_responde_401_o_403(self):
        self.assertIn(self.client.get("/api/actividades/").status_code, (401, 403))

    def test_lista_actividades_con_cupos(self):
        self.client.force_login(self.estudiante)
        datos = self.client.get("/api/actividades/").json()
        self.assertEqual(datos[0]["nombre"], "Club de lectura")
        self.assertEqual(datos[0]["cupos_disponibles"], 1)

    def test_inscripcion_por_api_y_duplicado_400(self):
        self.client.force_login(self.estudiante)
        primera = self.client.post("/api/inscripciones/", {"actividad": self.actividad.pk}, content_type="application/json")
        self.assertEqual(primera.status_code, 201)
        segunda = self.client.post("/api/inscripciones/", {"actividad": self.actividad.pk}, content_type="application/json")
        self.assertEqual(segunda.status_code, 400)
        self.assertIn("Ya estás inscrito", str(segunda.json()))

    def test_lider_no_puede_inscribirse_por_api(self):
        self.client.force_login(self.lider)
        respuesta = self.client.post("/api/inscripciones/", {"actividad": self.actividad.pk}, content_type="application/json")
        self.assertEqual(respuesta.status_code, 403)

    def test_mis_horas(self):
        self.client.force_login(self.estudiante)
        datos = self.client.get("/api/mis-horas/").json()
        self.assertEqual(datos["meta"], 60)
        self.assertEqual(datos["estado"], "En progreso")

    def test_indicadores_solo_para_bienestar_coordinador_admin(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get("/api/dashboard/").status_code, 403)
        self.client.force_login(self.bienestar)
        self.assertEqual(self.client.get("/api/dashboard/").json()["estudiantes"], 1)
