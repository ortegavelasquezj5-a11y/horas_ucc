from django.urls import path

from . import views
from .constancia import ConstanciaView, VerificarConstanciaView

app_name = "horas"

urlpatterns = [
    path("", views.MisHorasView.as_view(), name="mis_horas"),
    path("soporte/", views.SoporteView.as_view(), name="soporte"),
    path("aprobar/", views.AprobarView.as_view(), name="aprobar"),
    path("<int:pk>/revisar/", views.RevisarView.as_view(), name="revisar"),
    path("<int:pk>/soporte/", views.VerSoporteView.as_view(), name="ver_soporte"),
    path("constancia/", ConstanciaView.as_view(), name="constancia"),
    path("verificar/<str:codigo>/", VerificarConstanciaView.as_view(), name="verificar"),
]