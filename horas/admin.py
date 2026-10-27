from django.contrib import admin

from .models import Constancia, RegistroHoras


@admin.register(RegistroHoras)
class RegistroHorasAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "nombre_actividad", "tipo", "horas", "estado", "fecha_solicitud")
    list_filter = ("estado", "tipo")
    search_fields = ("nombre_actividad", "estudiante__codigo", "estudiante__apellidos")
    list_select_related = ("estudiante", "tipo")


@admin.register(Constancia)
class ConstanciaAdmin(admin.ModelAdmin):
    list_display = ("codigo_verificacion", "estudiante", "total_horas", "fecha_expedicion")
