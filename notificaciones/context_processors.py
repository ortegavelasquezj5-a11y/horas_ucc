def notificaciones_sin_leer(request):
    """Número de notificaciones sin leer, para el contador del menú."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {"notificaciones_sin_leer": usuario.notificaciones.filter(leida=False).count()}
