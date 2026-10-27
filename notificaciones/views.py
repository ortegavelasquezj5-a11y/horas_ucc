from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from .models import Notificacion


class NotificacionListView(LoginRequiredMixin, ListView):
    """Cada usuario ve solo sus notificaciones."""

    template_name = "notificaciones/lista.html"
    paginate_by = 15

    def get_queryset(self):
        consulta = self.request.user.notificaciones.all()
        if self.request.GET.get("filtro") == "sin_leer":
            consulta = consulta.filter(leida=False)
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["filtro"] = self.request.GET.get("filtro", "")
        return contexto


class MarcarLeidaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
        notificacion.leida = True
        notificacion.save(update_fields=["leida"])
        return redirect("notificaciones:lista")


class MarcarTodasView(LoginRequiredMixin, View):
    def post(self, request):
        request.user.notificaciones.filter(leida=False).update(leida=True)
        return redirect("notificaciones:lista")
