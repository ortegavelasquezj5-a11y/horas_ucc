from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from usuarios.permisos import EstudianteMixin, GestorActividadesMixin

from . import services
from .forms import ActividadForm
from .models import Actividad, Inscripcion, TipoActividad

Estado = Actividad.Estado


def _con_ocupados(consulta):
    return consulta.annotate(
        ocupados=Count("inscripciones", filter=Q(inscripciones__estado=Inscripcion.Estado.INSCRITO))
    )


# ---------------------------------------------------------------- Estudiante
class CatalogoView(EstudianteMixin, ListView):
    """Actividades publicadas que aún no empiezan."""

    template_name = "actividades/catalogo.html"
    paginate_by = 12

    def get_queryset(self):
        consulta = _con_ocupados(
            Actividad.objects.filter(estado=Estado.PUBLICADA, fecha_inicio__gt=timezone.now())
            .select_related("tipo", "responsable")
        ).order_by("fecha_inicio")
        self.tipo = self.request.GET.get("tipo", "")
        self.q = self.request.GET.get("q", "").strip()
        if self.tipo.isdigit():
            consulta = consulta.filter(tipo_id=self.tipo)
        if self.q:
            consulta = consulta.filter(Q(nombre__icontains=self.q) | Q(lugar__icontains=self.q))
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        inscritas = set(
            self.request.user.inscripciones.filter(estado=Inscripcion.Estado.INSCRITO)
            .values_list("actividad_id", flat=True)
        )
        for actividad in contexto["object_list"]:
            actividad.inscrito = actividad.pk in inscritas
            actividad.libres = max(actividad.cupo - actividad.ocupados, 0)
            actividad.ocupacion = round(actividad.ocupados / actividad.cupo * 100)
        contexto.update(tipos=TipoActividad.objects.all(), tipo=self.tipo, q=self.q)
        return contexto


class InscribirView(EstudianteMixin, View):
    def post(self, request, pk):
        actividad = get_object_or_404(Actividad, pk=pk)
        try:
            services.inscribir(request.user, actividad)
            messages.success(request, f"Te inscribiste en «{actividad.nombre}». "
                                      "Te avisaremos cuando se registre tu asistencia.")
        except services.ReglaDeNegocioError as error:
            messages.error(request, str(error))
        return redirect(request.POST.get("volver") or "actividades:catalogo")


class CancelarInscripcionView(EstudianteMixin, View):
    def post(self, request, pk):
        inscripcion = get_object_or_404(
            Inscripcion, actividad_id=pk, estudiante=request.user
        )
        try:
            services.cancelar_inscripcion(inscripcion, request.user)
            messages.success(request, "Cancelaste tu inscripción. El cupo quedó libre.")
        except services.ReglaDeNegocioError as error:
            messages.error(request, str(error))
        return redirect(request.POST.get("volver") or "actividades:catalogo")


# ---------------------------------------------------------------- Líder y Bienestar
class GestionView(GestorActividadesMixin, ListView):
    """El líder ve sus actividades; Bienestar y el administrador, todas."""

    template_name = "actividades/gestion.html"
    paginate_by = 15

    def get_queryset(self):
        consulta = _con_ocupados(Actividad.objects.select_related("tipo", "responsable"))
        if self.request.user.es_lider:
            consulta = consulta.filter(responsable=self.request.user)
        self.estado = self.request.GET.get("estado", "")
        if self.estado in Estado.values:
            consulta = consulta.filter(estado=self.estado)
        return consulta.order_by("-fecha_inicio")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        ahora = timezone.now()
        for a in contexto["object_list"]:
            empezo = a.fecha_inicio <= ahora
            a.puede_editar = a.estado in (Estado.BORRADOR, Estado.PUBLICADA) and not empezo
            a.puede_publicar = a.estado == Estado.BORRADOR and not empezo
            a.puede_asistencia = a.estado in (Estado.PUBLICADA, Estado.FINALIZADA) and empezo
            a.puede_cancelar = a.estado in (Estado.BORRADOR, Estado.PUBLICADA)
            a.pendiente_asistencia = a.estado == Estado.PUBLICADA and empezo
        contexto.update(estados=Estado.choices, estado=self.estado)
        return contexto


class _GuardarActividadMixin:
    form_class = ActividadForm
    template_name = "actividades/form.html"

    def form_valid(self, form):
        actividad = form.save(commit=False)
        if not actividad.pk:
            actividad.responsable = self.request.user
        actividad.save()
        self.object = actividad
        if self.request.POST.get("accion") == "publicar" and actividad.estado == Estado.BORRADOR:
            try:
                services.publicar(actividad, self.request.user)
                messages.success(self.request, "Actividad publicada. Ya la ven los estudiantes.")
            except services.ReglaDeNegocioError as error:
                messages.error(self.request, str(error))
        else:
            messages.success(self.request, "Actividad guardada.")
        return redirect("actividades:gestion")


class ActividadCreateView(GestorActividadesMixin, _GuardarActividadMixin, CreateView):
    model = Actividad


class ActividadUpdateView(GestorActividadesMixin, _GuardarActividadMixin, UpdateView):
    model = Actividad

    def get_object(self, queryset=None):
        actividad = super().get_object(queryset)
        if not services.puede_gestionar(self.request.user, actividad):
            raise PermissionDenied("Esta actividad está a cargo de otro líder.")
        if actividad.estado not in (Estado.BORRADOR, Estado.PUBLICADA) or actividad.ya_empezo:
            raise PermissionDenied("Solo se editan actividades que no han empezado.")
        return actividad


class _AccionActividadView(GestorActividadesMixin, View):
    accion = None
    mensaje = ""

    def post(self, request, pk):
        actividad = get_object_or_404(Actividad, pk=pk)
        try:
            getattr(services, self.accion)(actividad, request.user)
            messages.success(request, self.mensaje)
        except services.ReglaDeNegocioError as error:
            messages.error(request, str(error))
        return redirect("actividades:gestion")


class PublicarView(_AccionActividadView):
    accion = "publicar"
    mensaje = "Actividad publicada. Ya la ven los estudiantes."


class CancelarActividadView(_AccionActividadView):
    accion = "cancelar_actividad"
    mensaje = "Actividad cancelada. Se avisó a los inscritos."


class AsistenciaView(GestorActividadesMixin, TemplateView):
    template_name = "actividades/asistencia.html"

    def dispatch(self, request, *args, **kwargs):
        self.actividad = get_object_or_404(
            Actividad.objects.select_related("tipo"), pk=kwargs["pk"]
        )
        if request.user.is_authenticated and not services.puede_gestionar(request.user, self.actividad):
            raise PermissionDenied("Esta actividad está a cargo de otro líder.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        inscritos = list(self.actividad.inscritos.select_related("estudiante__programa", "registro_horas"))
        for i in inscritos:
            registro = getattr(i, "registro_horas", None)
            i.bloqueado = registro is not None and registro.estado != registro.Estado.POR_APROBAR
        contexto.update(
            actividad=self.actividad,
            inscritos=inscritos,
            asistieron=sum(1 for i in inscritos if i.asistio),
            se_puede=self.actividad.ya_empezo and self.actividad.estado in (Estado.PUBLICADA, Estado.FINALIZADA),
        )
        return contexto

    def post(self, request, pk):
        try:
            total = services.registrar_asistencia(
                self.actividad, request.user, request.POST.getlist("presentes")
            )
            messages.success(
                request, f"Asistencia guardada: {total} estudiante(s) asistieron. "
                         "Sus horas quedaron por aprobar en Bienestar."
            )
        except services.ReglaDeNegocioError as error:
            messages.error(request, str(error))
        return redirect(reverse("actividades:asistencia", args=[pk]))
