from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View

from .menu import opciones_menu


class InicioView(LoginRequiredMixin, View):
    """Después del login, lleva a cada rol a su pantalla principal."""

    def get(self, request):
        opciones = opciones_menu(request.user)
        if opciones:
            return redirect(opciones[0][1])
        return redirect("notificaciones:lista")
