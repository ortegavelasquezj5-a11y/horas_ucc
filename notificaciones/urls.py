from django.urls import path

from . import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.NotificacionListView.as_view(), name="lista"),
    path("<int:pk>/leida/", views.MarcarLeidaView.as_view(), name="leida"),
    path("todas-leidas/", views.MarcarTodasView.as_view(), name="todas_leidas"),
]
