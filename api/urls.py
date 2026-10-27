from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("actividades/", views.ActividadesDisponiblesView.as_view(), name="actividades"),
    path("inscripciones/", views.InscripcionCreateView.as_view(), name="inscripciones"),
    path("mis-horas/", views.MisHorasView.as_view(), name="mis_horas"),
    path("notificaciones/", views.NotificacionesView.as_view(), name="notificaciones"),
    path("dashboard/", views.IndicadoresView.as_view(), name="dashboard"),
]
