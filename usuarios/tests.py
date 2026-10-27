from django.test import TestCase
from django.urls import reverse

from .models import Programa, Usuario

Rol = Usuario.Rol


def crear_usuario(rol, codigo, programa=None, semestre=None, **extra):
    return Usuario.objects.create_user(
        correo=f"{codigo.lower()}@campusucc.edu.co", password="clave-segura-123",
        codigo=codigo, nombres="Nombre", apellidos=f"Apellido {codigo}",
        rol=rol, programa=programa, semestre=semestre, **extra,
    )


class AutenticacionTests(TestCase):
    def setUp(self):
        self.programa = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        self.estudiante = crear_usuario(Rol.ESTUDIANTE, "E001", self.programa, 6)

    def test_login_con_correo_institucional(self):
        respuesta = self.client.post(reverse("login"), {
            "username": "E001@campusucc.edu.co", "password": "clave-segura-123",
        })
        self.assertRedirects(respuesta, reverse("inicio"), fetch_redirect_response=False)

    def test_login_con_clave_incorrecta_muestra_error(self):
        respuesta = self.client.post(reverse("login"), {
            "username": "e001@campusucc.edu.co", "password": "otra-clave",
        })
        self.assertContains(respuesta, "Correo o contraseña incorrectos")

    def test_usuario_inactivo_no_puede_entrar(self):
        self.estudiante.is_active = False
        self.estudiante.save()
        respuesta = self.client.post(reverse("login"), {
            "username": "e001@campusucc.edu.co", "password": "clave-segura-123",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("notificaciones:lista"))
        self.assertRedirects(respuesta, "/login/?next=/notificaciones/")

    def test_solo_el_administrador_entra_al_panel_de_django(self):
        self.assertFalse(self.estudiante.is_staff)
        admin = crear_usuario(Rol.ADMIN, "A001")
        self.assertTrue(admin.is_staff)
