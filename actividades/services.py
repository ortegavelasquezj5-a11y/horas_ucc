"""Reglas de negocio de actividades, inscripciones y asistencia.

Las vistas web y la API llaman estas funciones: ninguna regla vive en las
vistas ni en las plantillas.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from horas.models import RegistroHoras
from notificaciones.services import notificar, notificar_a_varios
from usuarios.models import Usuario

from .models import Actividad, Inscripcion

Rol = Usuario.Rol


class ReglaDeNegocioError(Exception):
    """Se lanza cuando una operación viola una regla del negocio."""


def puede_gestionar(usuario, actividad):
    """El responsable de la actividad, Bienestar y el administrador."""
    return usuario.rol in (Rol.BIENESTAR, Rol.ADMIN) or actividad.responsable_id == usuario.id


def texto_horas(horas):
    """4.0 → '4 h' · 2.5 → '2,5 h'."""
    numero = f"{Decimal(str(horas)).normalize():f}"
    return numero.replace(".", ",") + " h"


def publicar(actividad, usuario):
    """Publica un borrador y avisa a los estudiantes."""
    if not puede_gestionar(usuario, actividad):
        raise ReglaDeNegocioError("Solo el responsable puede publicar esta actividad.")
    if actividad.estado != Actividad.Estado.BORRADOR:
        raise ReglaDeNegocioError("Solo se pueden publicar actividades en borrador.")
    if actividad.ya_empezo:
        raise ReglaDeNegocioError("No se puede publicar una actividad cuya fecha ya pasó.")
    actividad.estado = Actividad.Estado.PUBLICADA
    actividad.save(update_fields=["estado"])
    fecha = timezone.localtime(actividad.fecha_inicio).strftime("%d/%m/%Y")
    notificar_a_varios(
        Usuario.objects.filter(rol=Rol.ESTUDIANTE, is_active=True),
        f"Nueva actividad: «{actividad.nombre}» · {actividad.tipo} · "
        f"{texto_horas(actividad.horas_otorga)} · {fecha}.",
    )
    return actividad


@transaction.atomic
def cancelar_actividad(actividad, usuario):
    """Cancela la actividad, cancela las inscripciones y avisa a los inscritos."""
    if not puede_gestionar(usuario, actividad):
        raise ReglaDeNegocioError("Solo el responsable puede cancelar esta actividad.")
    if actividad.estado in (Actividad.Estado.FINALIZADA, Actividad.Estado.CANCELADA):
        raise ReglaDeNegocioError("La actividad ya está finalizada o cancelada.")
    inscritos = list(actividad.inscritos.select_related("estudiante"))
    actividad.estado = Actividad.Estado.CANCELADA
    actividad.save(update_fields=["estado"])
    actividad.inscripciones.filter(estado=Inscripcion.Estado.INSCRITO).update(
        estado=Inscripcion.Estado.CANCELADO
    )
    notificar_a_varios(
        [i.estudiante for i in inscritos],
        f"La actividad «{actividad.nombre}» fue cancelada.",
    )
    return actividad


@transaction.atomic
def inscribir(estudiante, actividad):
    """Inscribe a un estudiante validando estado, fecha, duplicados y cupo."""
    if not estudiante.es_estudiante:
        raise ReglaDeNegocioError("Solo los estudiantes pueden inscribirse en actividades.")
    if not estudiante.is_active:
        raise ReglaDeNegocioError("Tu usuario está inactivo.")

    # Bloquea la fila: dos inscripciones al mismo tiempo no pueden superar el cupo
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if actividad.estado != Actividad.Estado.PUBLICADA:
        raise ReglaDeNegocioError("La actividad no está abierta para inscripciones.")
    if actividad.ya_empezo:
        raise ReglaDeNegocioError("La actividad ya empezó; no se aceptan inscripciones.")

    existente = Inscripcion.objects.filter(estudiante=estudiante, actividad=actividad).first()
    if existente and existente.estado == Inscripcion.Estado.INSCRITO:
        raise ReglaDeNegocioError("Ya estás inscrito en esta actividad.")
    if actividad.cupos_disponibles <= 0:
        raise ReglaDeNegocioError("La actividad no tiene cupos disponibles.")

    if existente:  # había cancelado: se reactiva en lugar de duplicar
        existente.estado = Inscripcion.Estado.INSCRITO
        existente.asistio = None
        existente.save(update_fields=["estado", "asistio"])
        return existente
    return Inscripcion.objects.create(estudiante=estudiante, actividad=actividad)


def cancelar_inscripcion(inscripcion, estudiante):
    """El estudiante cancela antes de que empiece la actividad y libera el cupo."""
    if inscripcion.estudiante_id != estudiante.id:
        raise ReglaDeNegocioError("Esta inscripción no es tuya.")
    if inscripcion.estado != Inscripcion.Estado.INSCRITO:
        raise ReglaDeNegocioError("La inscripción ya estaba cancelada.")
    if inscripcion.actividad.ya_empezo:
        raise ReglaDeNegocioError("No puedes cancelar: la actividad ya empezó.")
    inscripcion.estado = Inscripcion.Estado.CANCELADO
    inscripcion.save(update_fields=["estado"])
    return inscripcion


@transaction.atomic
def registrar_asistencia(actividad, usuario, ids_presentes):
    """Marca quién asistió. A cada asistente le genera sus horas 'por aprobar'.

    Si se corrige la asistencia, las horas aún sin revisar se ajustan;
    las que Bienestar ya aprobó o rechazó no se modifican.
    """
    if not puede_gestionar(usuario, actividad):
        raise ReglaDeNegocioError("Solo el responsable de la actividad puede registrar la asistencia.")
    if actividad.estado not in (Actividad.Estado.PUBLICADA, Actividad.Estado.FINALIZADA):
        raise ReglaDeNegocioError("Solo se registra asistencia de actividades publicadas.")
    if not actividad.ya_empezo:
        raise ReglaDeNegocioError("La asistencia se registra cuando la actividad ya empezó.")

    presentes = {int(i) for i in ids_presentes}
    asistieron = 0
    for inscripcion in actividad.inscritos.select_related("estudiante"):
        asistio = inscripcion.estudiante_id in presentes
        registro = RegistroHoras.objects.filter(inscripcion=inscripcion).first()
        if registro and registro.estado != RegistroHoras.Estado.POR_APROBAR:
            asistieron += 1 if inscripcion.asistio else 0
            continue
        inscripcion.asistio = asistio
        inscripcion.save(update_fields=["asistio"])
        if asistio:
            asistieron += 1
            if not registro:
                RegistroHoras.objects.create(
                    estudiante=inscripcion.estudiante,
                    inscripcion=inscripcion,
                    nombre_actividad=actividad.nombre,
                    tipo=actividad.tipo,
                    fecha_actividad=timezone.localtime(actividad.fecha_inicio).date(),
                    horas=actividad.horas_otorga,
                )
                notificar(
                    inscripcion.estudiante,
                    f"Se registró tu asistencia a «{actividad.nombre}». "
                    f"Tus {texto_horas(actividad.horas_otorga)} quedaron por aprobar.",
                )
        elif registro:
            registro.delete()

    if actividad.estado != Actividad.Estado.FINALIZADA:
        actividad.estado = Actividad.Estado.FINALIZADA
        actividad.save(update_fields=["estado"])
    return asistieron
