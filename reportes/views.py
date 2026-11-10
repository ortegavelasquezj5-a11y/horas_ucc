from django.core.paginator import Paginator
from django.views.generic import TemplateView

from horas import services
from usuarios.models import Programa
from usuarios.permisos import SeguimientoMixin

from .services import indicadores


def programa_elegido(request):
    """El coordinador ve solo su programa; Bienestar y el administrador eligen."""
    if request.user.es_coordinador:
        return request.user.programa, []
    programas = Programa.objects.all()
    elegido = request.GET.get("programa", "")
    return (programas.filter(pk=elegido).first() if elegido.isdigit() else None), programas


class DashboardView(SeguimientoMixin, TemplateView):
    """Indicadores generales y gráficas de participación (HU-12)."""

    template_name = "reportes/dashboard.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        programa, programas = programa_elegido(self.request)
        datos = indicadores(programa)
        # Datos para Chart.js (static/js/dashboard.js); se pasan con json_script
        graficas = {
            "porTipo": {"etiquetas": [t["nombre"] for t in datos["por_tipo"]],
                        "valores": [float(t["valor"]) for t in datos["por_tipo"]]},
            "porMes": {"etiquetas": [m["nombre"] for m in datos["por_mes"]],
                       "valores": [float(m["valor"]) for m in datos["por_mes"]]},
            "cumplimiento": {"etiquetas": [c["texto"] for c in datos["cumplimiento"]],
                             "valores": [c["total"] for c in datos["cumplimiento"]]},
            "porPrograma": {"etiquetas": [p["programa"] for p in datos["por_programa"]],
                            "promedio": [float(p["promedio"]) for p in datos["por_programa"]],
                            "meta": [p["meta"] for p in datos["por_programa"]]},
        }
        contexto.update(programa=programa, programas=programas, datos=datos, graficas=graficas)
        return contexto


class SeguimientoView(SeguimientoMixin, TemplateView):
    """Estudiantes con sus horas y su estado de cumplimiento (HU-11)."""

    template_name = "reportes/seguimiento.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        get = self.request.GET
        programa, programas = programa_elegido(self.request)

        semestre = get.get("semestre", "")
        filas = services.seguimiento(programa=programa, semestre=int(semestre) if semestre.isdigit() else None)
        conteo = {clave: sum(1 for f in filas if f["estado"] == clave) for clave in services.ESTADOS_CUMPLIMIENTO}
        q = get.get("q", "").strip().lower()
        if q:
            filas = [f for f in filas if q in f["estudiante"].nombre_completo.lower() or q in f["estudiante"].codigo.lower()]
        estado = get.get("estado", "")
        if estado in services.ESTADOS_CUMPLIMIENTO:
            filas = [f for f in filas if f["estado"] == estado]

        # Paginación: 15 estudiantes por página, conservando los filtros en la URL
        pagina = Paginator(filas, 15).get_page(get.get("page"))
        contexto.update(
            filas=pagina.object_list,
            page_obj=pagina,
            paginator=pagina.paginator,
            is_paginated=pagina.has_other_pages(),
            total_filas=len(filas),
            programa=programa,
            programas=programas,
            semestre=semestre,
            semestres=range(1, 11),
            estado=estado,
            q=get.get("q", "").strip(),
            estados=services.ESTADOS_CUMPLIMIENTO,
            resumen=[(clave, services.ESTADOS_CUMPLIMIENTO[clave], conteo[clave]) for clave in services.ESTADOS_CUMPLIMIENTO],
            semestre_riesgo=services.SEMESTRE_RIESGO,
        )
        return contexto