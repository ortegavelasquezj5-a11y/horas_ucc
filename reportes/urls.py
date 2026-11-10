from django.urls import path

from . import views
from .reporte_excel import ExportarExcelView

app_name = "reportes"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("seguimiento/", views.SeguimientoView.as_view(), name="seguimiento"),
    path("seguimiento/excel/", ExportarExcelView.as_view(), name="excel"),
]