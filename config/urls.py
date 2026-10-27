"""Rutas principales del proyecto."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from usuarios.views import InicioView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("usuarios/", include("usuarios.urls")),
    path("actividades/", include("actividades.urls")),
    path("horas/", include("horas.urls")),
    path("seguimiento/", include("reportes.urls")),
    path("notificaciones/", include("notificaciones.urls")),
    path("api/", include("api.urls")),
    path("", InicioView.as_view(), name="inicio"),
]
# Los soportes NO se publican en /media/: se descargan por horas:ver_soporte,
# que revisa que quien los pida sea el dueño o Bienestar.
