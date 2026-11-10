"""Constancia de horas aprobadas (HU-10).

La constancia es una página lista para imprimir: el botón «Guardar como PDF»
usa la impresión del navegador. Cada constancia queda registrada con un código
único que cualquiera puede verificar en /horas/verificar/<código>/.
"""
import secrets

from django.shortcuts import render
from django.urls import reverse
from django.views import View

from usuarios.permisos import EstudianteMixin

from . import services
from .models import Constancia, RegistroHoras

LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para que no se confundan


def nuevo_codigo():
    while True:
        codigo = "UCC-" + "".join(secrets.choice(LETRAS) for _ in range(8))
        if not Constancia.objects.filter(codigo_verificacion=codigo).exists():
            return codigo


def generar_constancia(estudiante):
    """Reutiliza la última constancia si las horas no han cambiado; si no, crea otra."""
    total = services.resumen_horas(estudiante)["aprobadas"]
    ultima = estudiante.constancias.first()
    if ultima and ultima.total_horas == total:
        return ultima
    return Constancia.objects.create(
        estudiante=estudiante, codigo_verificacion=nuevo_codigo(), total_horas=total
    )


class ConstanciaView(EstudianteMixin, View):
    def get(self, request):
        estudiante = request.user
        constancia = generar_constancia(estudiante)
        registros = (
            estudiante.registros_horas.filter(estado=RegistroHoras.Estado.APROBADA)
            .select_related("tipo")
            .order_by("fecha_actividad")
        )
        url_verificacion = request.build_absolute_uri(
            reverse("horas:verificar", args=[constancia.codigo_verificacion])
        )
        return render(request, "horas/constancia.html", {
            "estudiante": estudiante,
            "constancia": constancia,
            "registros": registros,
            "resumen": services.resumen_horas(estudiante),
            "url_verificacion": url_verificacion,
        })


class VerificarConstanciaView(View):
    """Página pública: confirma si un código de constancia es válido."""

    def get(self, request, codigo):
        constancia = (
            Constancia.objects.select_related("estudiante__programa")
            .filter(codigo_verificacion=codigo.strip().upper()).first()
        )
        return render(request, "horas/verificar.html", {"constancia": constancia, "codigo": codigo})