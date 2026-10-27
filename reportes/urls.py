from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("seguimiento/", views.SeguimientoView.as_view(), name="seguimiento"),
]
