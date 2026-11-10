from django.urls import path

from . import views

app_name = "actividades"

urlpatterns = [
    # Estudiante
    path("", views.CatalogoView.as_view(), name="catalogo"),
    path("<int:pk>/inscribir/", views.InscribirView.as_view(), name="inscribir"),
    path("<int:pk>/cancelar-inscripcion/", views.CancelarInscripcionView.as_view(), name="cancelar_inscripcion"),
    # Líder, Bienestar y administrador
    path("gestion/", views.GestionView.as_view(), name="gestion"),
    path("nueva/", views.ActividadCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.ActividadUpdateView.as_view(), name="editar"),
    path("<int:pk>/publicar/", views.PublicarView.as_view(), name="publicar"),
    path("<int:pk>/cancelar/", views.CancelarActividadView.as_view(), name="cancelar"),
    path("<int:pk>/eliminar/", views.ActividadDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/asistencia/", views.AsistenciaView.as_view(), name="asistencia"),
]
