"""Indicadores del dashboard (HU-12). Cada indicador sale de una consulta agrupada."""
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from actividades.models import Actividad, Inscripcion
from horas.models import RegistroHoras
from horas.services import ESTADOS_CUMPLIMIENTO, seguimiento

APROBADA = RegistroHoras.Estado.APROBADA
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _barras(filas, clave, valor):
    """Agrega a cada fila el ancho de su barra (%) frente al mayor valor."""
    maximo = max((f[valor] for f in filas), default=0) or 1
    return [{"nombre": f[clave], "valor": f[valor], "ancho": round(f[valor] / maximo * 100)} for f in filas]


def _ultimos_meses(cantidad=6):
    hoy = timezone.localdate()
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append(date(anio, mes, 1))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(meses))


def indicadores(programa=None):
    """Todo lo que muestra el dashboard. Si hay programa, se filtra por él."""
    registros = RegistroHoras.objects.all()
    inscripciones = Inscripcion.objects.filter(estado=Inscripcion.Estado.INSCRITO, asistio__isnull=False)
    if programa:
        registros = registros.filter(estudiante__programa=programa)
        inscripciones = inscripciones.filter(estudiante__programa=programa)
    aprobados = registros.filter(estado=APROBADA)

    # Cumplimiento por estudiante (una sola consulta)
    filas = seguimiento(programa=programa)
    conteo = {clave: sum(1 for f in filas if f["estado"] == clave) for clave in ESTADOS_CUMPLIMIENTO}
    total_estudiantes = len(filas)

    # Asistencia: de los inscritos con asistencia registrada, cuántos fueron
    asistencia = inscripciones.aggregate(total=Count("id"), fueron=Count("id", filter=Q(asistio=True)))

    # Horas aprobadas por tipo de actividad
    por_tipo = list(
        aprobados.values("tipo__nombre").annotate(total=Sum("horas")).order_by("-total")
    )

    # Horas aprobadas por mes (últimos 6 meses, por fecha de la actividad)
    meses = _ultimos_meses()
    por_mes_bd = {
        f["mes"]: f["total"]
        for f in aprobados.filter(fecha_actividad__gte=meses[0])
        .annotate(mes=TruncMonth("fecha_actividad"))
        .values("mes").annotate(total=Sum("horas"))
    }
    por_mes = [{"nombre": f"{MESES[m.month - 1]} {m.year % 100:02d}", "total": por_mes_bd.get(m, Decimal("0"))} for m in meses]

    # Resumen por programa
    por_programa = {}
    for f in filas:
        nombre = f["estudiante"].programa.nombre
        p = por_programa.setdefault(nombre, {"programa": nombre, "estudiantes": 0, "horas": Decimal("0"), "cumplen": 0, "meta": f["meta"]})
        p["estudiantes"] += 1
        p["horas"] += f["horas"]
        p["cumplen"] += 1 if f["estado"] == "cumple" else 0
    tabla_programas = sorted(por_programa.values(), key=lambda p: p["programa"])
    for p in tabla_programas:
        p["promedio"] = (p["horas"] / p["estudiantes"]).quantize(Decimal("0.1"))
        p["porcentaje"] = round(p["cumplen"] / p["estudiantes"] * 100)

    actividades = Actividad.objects.filter(estado=Actividad.Estado.FINALIZADA)
    if programa:
        actividades = actividades.filter(inscripciones__estudiante__programa=programa).distinct()

    return {
        "horas_aprobadas": aprobados.aggregate(t=Sum("horas"))["t"] or Decimal("0"),
        "total_estudiantes": total_estudiantes,
        "cumplen": conteo["cumple"],
        "porcentaje_cumplen": round(conteo["cumple"] / total_estudiantes * 100) if total_estudiantes else 0,
        "actividades_realizadas": actividades.count(),
        "asistencia_promedio": round(asistencia["fueron"] / asistencia["total"] * 100) if asistencia["total"] else 0,
        "por_aprobar": registros.filter(estado=RegistroHoras.Estado.POR_APROBAR).count(),
        "por_tipo": _barras(por_tipo, "tipo__nombre", "total"),
        "por_mes": _barras(por_mes, "nombre", "total"),
        "cumplimiento": [
            {"clave": clave, "texto": texto, "total": conteo[clave],
             "porcentaje": round(conteo[clave] / total_estudiantes * 100) if total_estudiantes else 0}
            for clave, texto in ESTADOS_CUMPLIMIENTO.items()
        ],
        "por_programa": tabla_programas,
    }