"""Menú lateral de cada rol. Cada rol ve solo sus opciones."""
from django.urls import NoReverseMatch, reverse

from .models import Usuario

Rol = Usuario.Rol

MENUS = {
    Rol.ESTUDIANTE: [
        ("Mis horas", "horas:mis_horas"),
        ("Actividades", "actividades:catalogo"),
        ("Cargar soporte", "horas:soporte"),
        ("Notificaciones", "notificaciones:lista"),
    ],
    Rol.LIDER: [
        ("Mis actividades", "actividades:gestion"),
        ("Nueva actividad", "actividades:crear"),
        ("Notificaciones", "notificaciones:lista"),
    ],
    Rol.BIENESTAR: [
        ("Aprobar horas", "horas:aprobar"),
        ("Actividades", "actividades:gestion"),
        ("Nueva actividad", "actividades:crear"),
        ("Seguimiento", "reportes:seguimiento"),
        ("Notificaciones", "notificaciones:lista"),
    ],
    Rol.COORDINADOR: [
        ("Seguimiento", "reportes:seguimiento"),
        ("Notificaciones", "notificaciones:lista"),
    ],
    Rol.ADMIN: [
        ("Usuarios", "usuarios:lista"),
        ("Programas", "usuarios:programas"),
        ("Aprobar horas", "horas:aprobar"),
        ("Actividades", "actividades:gestion"),
        ("Seguimiento", "reportes:seguimiento"),
        ("Notificaciones", "notificaciones:lista"),
    ],
}


def opciones_menu(usuario):
    """Lista de (texto, url) del menú del usuario."""
    opciones = []
    for texto, nombre_url in MENUS.get(usuario.rol, []):
        try:
            opciones.append((texto, reverse(nombre_url)))
        except NoReverseMatch:  # módulo aún no disponible
            continue
    return opciones


def menu(request):
    """Procesador de contexto: entrega el menú a todas las plantillas."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {"menu_lateral": opciones_menu(usuario)}
