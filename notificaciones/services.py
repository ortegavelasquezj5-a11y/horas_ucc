"""Creación de notificaciones. Las usan los demás módulos."""
from .models import Notificacion


def notificar(usuario, mensaje):
    return Notificacion.objects.create(usuario=usuario, mensaje=mensaje[:255])


def notificar_a_varios(usuarios, mensaje):
    Notificacion.objects.bulk_create(
        [Notificacion(usuario=u, mensaje=mensaje[:255]) for u in usuarios]
    )
