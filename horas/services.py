"""Reglas de negocio de las horas: soportes externos, aprobación y acumulado."""
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from actividades.services import ReglaDeNegocioError
from notificaciones.services import notificar
from usuarios.models import Usuario

from .models import RegistroHoras

Rol = Usuario.Rol
Estado = RegistroHoras.Estado

EXTENSIONES_SOPORTE = {".pdf", ".jpg", ".jpeg", ".png"}
HORAS_MAXIMAS_EXTERNA = Decimal("40")
SEMESTRE_RIESGO = 8  # desde este semestre, sin cumplir la meta = en riesgo
CERO = Value(Decimal("0"), output_field=DecimalField(max_digits=6, decimal_places=1))

ESTADOS_CUMPLIMIENTO = {
    "cumple": "Cumple",
    "en-progreso": "En progreso",
    "en-riesgo": "En riesgo",
}


def _a_decimal(valor, mensaje):
    try:
        return Decimal(str(valor)).quantize(Decimal("0.1"))
    except (InvalidOperation, ValueError, TypeError):
        raise ReglaDeNegocioError(mensaje)


def validar_soporte(archivo):
    if not archivo:
        raise ReglaDeNegocioError("El soporte es obligatorio.")
    if Path(archivo.name).suffix.lower() not in EXTENSIONES_SOPORTE:
        raise ReglaDeNegocioError("El soporte debe ser PDF, JPG o PNG.")
    if archivo.size > settings.TAMANO_MAXIMO_SOPORTE:
        raise ReglaDeNegocioError("El soporte no puede pesar más de 5 MB.")


def solicitar_horas_externas(estudiante, nombre_actividad, tipo, fecha_actividad, horas, soporte):
    """El estudiante pide que se le reconozcan horas de una actividad externa."""
    if not estudiante.es_estudiante:
        raise ReglaDeNegocioError("Solo los estudiantes pueden solicitar horas.")
    horas = _a_decimal(horas, "Las horas deben ser un número.")
    if horas <= 0:
        raise ReglaDeNegocioError("Las horas deben ser mayores que 0.")
    if horas > HORAS_MAXIMAS_EXTERNA:
        raise ReglaDeNegocioError("Una sola actividad externa no puede pasar de 40 horas.")
    if fecha_actividad > timezone.localdate():
        raise ReglaDeNegocioError("La fecha de la actividad no puede ser futura.")
    validar_soporte(soporte)
    return RegistroHoras.objects.create(
        estudiante=estudiante,
        nombre_actividad=nombre_actividad.strip(),
        tipo=tipo,
        fecha_actividad=fecha_actividad,
        horas=horas,
        soporte=soporte,
    )


def _validar_revision(registro, revisor):
    if revisor.rol not in (Rol.BIENESTAR, Rol.ADMIN):
        raise ReglaDeNegocioError("Solo Bienestar puede aprobar o rechazar horas.")
    if registro.estado != Estado.POR_APROBAR:
        raise ReglaDeNegocioError("Esta solicitud ya fue revisada.")


@transaction.atomic
def aprobar(registro, revisor, horas=None, motivo=""):
    """Aprueba las horas. Si Bienestar las ajusta, debe escribir el motivo."""
    _validar_revision(registro, revisor)
    motivo = (motivo or "").strip()
    if horas not in (None, ""):
        horas = _a_decimal(horas, "Las horas deben ser un número.")
        if horas <= 0:
            raise ReglaDeNegocioError("Las horas deben ser mayores que 0.")
        if horas != registro.horas:
            if not motivo:
                raise ReglaDeNegocioError("Escribe el motivo del ajuste de horas.")
            registro.horas = horas
    registro.estado = Estado.APROBADA
    registro.motivo = motivo
    registro.aprobador = revisor
    registro.fecha_revision = timezone.now()
    registro.save()
    notificar(
        registro.estudiante,
        f"Bienestar aprobó {registro.horas:g} h de «{registro.nombre_actividad}». "
        "Ya suman a tu acumulado.",
    )
    return registro


@transaction.atomic
def rechazar(registro, revisor, motivo):
    """Rechaza la solicitud. El motivo es obligatorio y el estudiante lo ve."""
    _validar_revision(registro, revisor)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ReglaDeNegocioError("Escribe el motivo del rechazo.")
    registro.estado = Estado.RECHAZADA
    registro.motivo = motivo
    registro.aprobador = revisor
    registro.fecha_revision = timezone.now()
    registro.save()
    notificar(
        registro.estudiante,
        f"Tu solicitud de «{registro.nombre_actividad}» fue rechazada. Motivo: {motivo}",
    )
    return registro


def estado_cumplimiento(aprobadas, meta, semestre):
    if meta and aprobadas >= meta:
        return "cumple"
    if (semestre or 0) >= SEMESTRE_RIESGO:
        return "en-riesgo"
    return "en-progreso"


def resumen_horas(estudiante):
    """Acumulado del estudiante frente a la meta de su programa."""
    totales = estudiante.registros_horas.aggregate(
        aprobadas=Coalesce(Sum("horas", filter=Q(estado=Estado.APROBADA)), CERO),
        por_aprobar=Coalesce(Sum("horas", filter=Q(estado=Estado.POR_APROBAR)), CERO),
    )
    meta = estudiante.programa.meta_horas if estudiante.programa else 0
    aprobadas = totales["aprobadas"]
    por_tipo = (
        estudiante.registros_horas.filter(estado=Estado.APROBADA)
        .values("tipo__nombre")
        .annotate(total=Sum("horas"))
        .order_by("-total")
    )
    maximo = max([t["total"] for t in por_tipo], default=0)
    estado = estado_cumplimiento(aprobadas, meta, estudiante.semestre)
    return {
        "meta": meta,
        "aprobadas": aprobadas,
        "por_aprobar": totales["por_aprobar"],
        "faltan": max(Decimal(meta) - aprobadas, Decimal("0")),
        "porcentaje": min(round(aprobadas / meta * 100), 100) if meta else 0,
        "por_tipo": [
            {"nombre": t["tipo__nombre"], "horas": t["total"],
             "ancho": round(t["total"] / maximo * 100) if maximo else 0}
            for t in por_tipo
        ],
        "estado": estado,
        "estado_texto": ESTADOS_CUMPLIMIENTO[estado],
    }


def seguimiento(programa=None, semestre=None):
    """Estudiantes con sus horas aprobadas y su estado, en una sola consulta."""
    estudiantes = (
        Usuario.objects.filter(rol=Rol.ESTUDIANTE, is_active=True)
        .select_related("programa")
        .annotate(
            horas_aprobadas=Coalesce(
                Sum("registros_horas__horas", filter=Q(registros_horas__estado=Estado.APROBADA)),
                CERO,
            )
        )
        .order_by("-semestre", "apellidos")
    )
    if programa is not None:
        estudiantes = estudiantes.filter(programa=programa)
    if semestre:
        estudiantes = estudiantes.filter(semestre=semestre)
    filas = []
    for e in estudiantes:
        meta = e.programa.meta_horas if e.programa else 0
        estado = estado_cumplimiento(e.horas_aprobadas, meta, e.semestre)
        filas.append({
            "estudiante": e,
            "horas": e.horas_aprobadas,
            "meta": meta,
            "porcentaje": min(round(e.horas_aprobadas / meta * 100), 100) if meta else 0,
            "estado": estado,
            "estado_texto": ESTADOS_CUMPLIMIENTO[estado],
        })
    return filas
