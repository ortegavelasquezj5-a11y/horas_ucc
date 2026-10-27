from django.contrib import admin

from .models import Programa, Usuario


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "meta_horas")
    search_fields = ("nombre",)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "apellidos", "nombres", "correo", "rol", "programa", "semestre", "is_active")
    list_filter = ("rol", "programa", "is_active")
    search_fields = ("codigo", "nombres", "apellidos", "correo")
    exclude = ("password", "groups", "user_permissions", "last_login")
