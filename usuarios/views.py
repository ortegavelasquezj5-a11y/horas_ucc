from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import ProgramaForm, UsuarioForm
from .menu import opciones_menu
from .models import Programa, Usuario
from .permisos import AdminMixin


class InicioView(LoginRequiredMixin, View):
    """Después del login, lleva a cada rol a su pantalla principal."""

    def get(self, request):
        opciones = opciones_menu(request.user)
        if opciones:
            return redirect(opciones[0][1])
        return redirect("notificaciones:lista")


class UsuarioListView(AdminMixin, ListView):
    template_name = "usuarios/lista.html"
    paginate_by = 15

    def get_queryset(self):
        consulta = Usuario.objects.select_related("programa")
        self.rol = self.request.GET.get("rol", "")
        self.q = self.request.GET.get("q", "").strip()
        if self.rol in Usuario.Rol.values:
            consulta = consulta.filter(rol=self.rol)
        if self.q:
            consulta = consulta.filter(
                Q(codigo__icontains=self.q) | Q(nombres__icontains=self.q)
                | Q(apellidos__icontains=self.q) | Q(correo__icontains=self.q)
            )
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(roles=Usuario.Rol.choices, rol=self.rol, q=self.q)
        return contexto


class UsuarioCreateView(AdminMixin, SuccessMessageMixin, CreateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")
    success_message = "Usuario %(codigo)s creado."


class UsuarioUpdateView(AdminMixin, SuccessMessageMixin, UpdateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")
    success_message = "Usuario %(codigo)s actualizado."


class CambiarEstadoUsuarioView(AdminMixin, View):
    """Activar o desactivar. Un usuario inactivo no puede iniciar sesión."""

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario == request.user:
            messages.error(request, "No puedes desactivar tu propio usuario.")
        else:
            usuario.is_active = not usuario.is_active
            usuario.save(update_fields=["is_active"])
            estado = "activado" if usuario.is_active else "desactivado: ya no podrá iniciar sesión"
            messages.success(request, f"{usuario.nombre_completo} fue {estado}.")
        return redirect(request.POST.get("volver") or "usuarios:lista")


class ProgramaListView(AdminMixin, ListView):
    template_name = "usuarios/programas.html"

    def get_queryset(self):
        return Programa.objects.annotate(
            estudiantes=Count("usuarios", filter=Q(usuarios__rol=Usuario.Rol.ESTUDIANTE))
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["form"] = kwargs.get("form") or ProgramaForm()
        return contexto

    def post(self, request):
        form = ProgramaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Programa creado.")
            return redirect("usuarios:programas")
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(form=form))


class ProgramaUpdateView(AdminMixin, SuccessMessageMixin, UpdateView):
    model = Programa
    form_class = ProgramaForm
    template_name = "usuarios/programa_form.html"
    success_url = reverse_lazy("usuarios:programas")
    success_message = "Programa actualizado. La nueva meta ya la ven los estudiantes."
