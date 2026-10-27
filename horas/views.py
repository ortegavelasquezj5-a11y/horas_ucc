from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from actividades.models import Inscripcion, TipoActividad
from actividades.services import ReglaDeNegocioError, texto_horas
from usuarios.permisos import BienestarMixin, EstudianteMixin

from . import services
from .forms import RevisionForm, SoporteForm
from .models import RegistroHoras

Estado = RegistroHoras.Estado


class MisHorasView(EstudianteMixin, TemplateView):
    """Acumulado del estudiante, horas por tipo e historial."""

    template_name = "horas/mis_horas.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        estudiante = self.request.user
        tipo = self.request.GET.get("tipo", "")

        historial = []
        registros = estudiante.registros_horas.select_related("tipo")
        if tipo.isdigit():
            registros = registros.filter(tipo_id=tipo)
        for r in registros:
            historial.append({
                "actividad": r.nombre_actividad, "tipo": r.tipo.nombre, "fecha": r.fecha_actividad,
                "horas": r.horas, "estado": r.estado, "estado_texto": r.get_estado_display(),
                "motivo": r.motivo if r.estado == Estado.RECHAZADA or r.motivo else "",
                "externa": r.es_externa,
            })
        # Inscripciones que todavía no generan horas
        pendientes = (
            estudiante.inscripciones.filter(estado=Inscripcion.Estado.INSCRITO, registro_horas__isnull=True)
            .exclude(asistio=False)
            .select_related("actividad__tipo")
        )
        if tipo.isdigit():
            pendientes = pendientes.filter(actividad__tipo_id=tipo)
        for i in pendientes:
            historial.append({
                "actividad": i.actividad.nombre, "tipo": i.actividad.tipo.nombre,
                "fecha": timezone.localtime(i.actividad.fecha_inicio).date(),
                "horas": i.actividad.horas_otorga, "estado": "inscrito", "estado_texto": "Inscrito",
                "motivo": "", "externa": False,
            })
        historial.sort(key=lambda h: h["fecha"], reverse=True)

        contexto.update(
            resumen=services.resumen_horas(estudiante),
            historial=historial,
            tipos=TipoActividad.objects.all(),
            tipo=tipo,
        )
        return contexto


class SoporteView(EstudianteMixin, FormView):
    """Cargar el soporte de una actividad externa."""

    template_name = "horas/soporte.html"
    form_class = SoporteForm

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["solicitudes"] = self.request.user.registros_horas.filter(
            inscripcion__isnull=True
        ).select_related("tipo")[:10]
        return contexto

    def form_valid(self, form):
        try:
            services.solicitar_horas_externas(self.request.user, **form.cleaned_data)
        except ReglaDeNegocioError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, "Solicitud enviada. Bienestar revisará tu soporte.")
        return redirect("horas:soporte")


class AprobarView(BienestarMixin, TemplateView):
    """Bandeja de Bienestar: lista de pendientes y detalle de la seleccionada."""

    template_name = "horas/aprobar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        pendientes = list(
            RegistroHoras.objects.filter(estado=Estado.POR_APROBAR)
            .select_related("estudiante__programa", "tipo", "inscripcion__actividad__responsable")
            .order_by("fecha_solicitud")
        )
        elegido = self.request.GET.get("id", "")
        seleccionado = next((r for r in pendientes if str(r.pk) == elegido), pendientes[0] if pendientes else None)
        form = kwargs.get("form")
        if form is None and seleccionado:
            form = RevisionForm(initial={"horas": seleccionado.horas})
        contexto.update(
            pendientes=pendientes,
            seleccionado=seleccionado,
            form=form,
            revisadas=RegistroHoras.objects.exclude(estado=Estado.POR_APROBAR)
            .select_related("estudiante", "aprobador").order_by("-fecha_revision")[:8],
        )
        return contexto


class RevisarView(BienestarMixin, View):
    def post(self, request, pk):
        registro = get_object_or_404(RegistroHoras, pk=pk)
        form = RevisionForm(request.POST)
        if not form.is_valid():
            errores = " ".join(e for lista in form.errors.values() for e in lista)
            messages.error(request, f"Revisa los datos: {errores}")
            return redirect(f"{reverse('horas:aprobar')}?id={pk}")
        datos = form.cleaned_data
        try:
            if datos["accion"] == "aprobar":
                services.aprobar(registro, request.user, datos.get("horas"), datos.get("motivo"))
                messages.success(request, f"Se aprobaron {texto_horas(registro.horas)} a {registro.estudiante.nombre_completo}.")
            else:
                services.rechazar(registro, request.user, datos.get("motivo"))
                messages.success(request, f"Solicitud de {registro.estudiante.nombre_completo} rechazada. Se le notificó el motivo.")
        except ReglaDeNegocioError as error:
            messages.error(request, str(error))
            return redirect(f"{reverse('horas:aprobar')}?id={pk}")
        return redirect("horas:aprobar")


class VerSoporteView(View):
    """Descarga del soporte: solo el dueño, Bienestar o el administrador."""

    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        registro = get_object_or_404(RegistroHoras, pk=pk)
        if not (registro.estudiante_id == request.user.id or request.user.rol in ("bienestar", "administrador")):
            raise PermissionDenied("No puedes ver este soporte.")
        if not registro.soporte:
            raise Http404("Esta solicitud no tiene soporte.")
        try:
            return FileResponse(registro.soporte.open("rb"), filename=registro.soporte.name.rsplit("/", 1)[-1])
        except FileNotFoundError:
            raise Http404("El archivo del soporte no se encuentra.")
