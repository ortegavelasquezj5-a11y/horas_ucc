from django.contrib import admin

from .models import Actividad, Inscripcion, TipoActividad


@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre",)


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "fecha_inicio", "cupo", "horas_otorga", "estado", "responsable")
    list_filter = ("estado", "tipo")
    search_fields = ("nombre",)
    list_select_related = ("tipo", "responsable")


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "actividad", "estado", "asistio", "fecha_inscripcion")
    list_filter = ("estado", "asistio")
    list_select_related = ("estudiante", "actividad")
