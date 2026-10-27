from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="lista"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/estado/", views.CambiarEstadoUsuarioView.as_view(), name="estado"),
    path("programas/", views.ProgramaListView.as_view(), name="programas"),
    path("programas/<int:pk>/editar/", views.ProgramaUpdateView.as_view(), name="programa_editar"),
]
