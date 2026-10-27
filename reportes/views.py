from django.views.generic import TemplateView

from horas import services
from usuarios.models import Programa
from usuarios.permisos import SeguimientoMixin


class SeguimientoView(SeguimientoMixin, TemplateView):
    """El coordinador ve su programa; Bienestar y el administrador eligen programa."""

    template_name = "reportes/seguimiento.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        get = self.request.GET

        if usuario.es_coordinador:
            programa = usuario.programa
            programas = []
        else:
            programas = Programa.objects.all()
            elegido = get.get("programa", "")
            programa = programas.filter(pk=elegido).first() if elegido.isdigit() else None

        semestre = get.get("semestre", "")
        filas = services.seguimiento(programa=programa, semestre=int(semestre) if semestre.isdigit() else None)
        conteo = {clave: sum(1 for f in filas if f["estado"] == clave) for clave in services.ESTADOS_CUMPLIMIENTO}
        estado = get.get("estado", "")
        if estado in services.ESTADOS_CUMPLIMIENTO:
            filas = [f for f in filas if f["estado"] == estado]

        contexto.update(
            filas=filas,
            programa=programa,
            programas=programas,
            semestre=semestre,
            semestres=range(1, 11),
            estado=estado,
            estados=services.ESTADOS_CUMPLIMIENTO,
            resumen=[(clave, services.ESTADOS_CUMPLIMIENTO[clave], conteo[clave]) for clave in services.ESTADOS_CUMPLIMIENTO],
            semestre_riesgo=services.SEMESTRE_RIESGO,
        )
        return contexto
