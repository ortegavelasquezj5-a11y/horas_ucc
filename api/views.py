"""API REST. Reutiliza la misma lógica de negocio que las pantallas web."""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from actividades.models import Actividad, Inscripcion
from horas import services as horas_services
from horas.models import RegistroHoras
from usuarios.models import Usuario

from .serializers import ActividadSerializer, InscripcionSerializer, NotificacionSerializer

Rol = Usuario.Rol


class TieneRol(permissions.BasePermission):
    """Permite el acceso solo a los roles indicados en la vista (atributo `roles`)."""

    message = "Tu rol no tiene acceso a este servicio."

    def has_permission(self, request, view):
        roles = getattr(view, "roles", ())
        return bool(request.user and request.user.is_authenticated and (not roles or request.user.rol in roles))


class ActividadesDisponiblesView(generics.ListAPIView):
    """GET /api/actividades/ · actividades publicadas con sus cupos libres."""

    serializer_class = ActividadSerializer
    permission_classes = [TieneRol]

    def get_queryset(self):
        return (
            Actividad.objects.filter(estado=Actividad.Estado.PUBLICADA, fecha_inicio__gt=timezone.now())
            .select_related("tipo", "responsable")
            .annotate(ocupados=Count("inscripciones", filter=Q(inscripciones__estado=Inscripcion.Estado.INSCRITO)))
            .order_by("fecha_inicio")
        )


class InscripcionCreateView(generics.CreateAPIView):
    """POST /api/inscripciones/ · {"actividad": id} inscribe al estudiante."""

    serializer_class = InscripcionSerializer
    permission_classes = [TieneRol]
    roles = (Rol.ESTUDIANTE,)


class MisHorasView(APIView):
    """GET /api/mis-horas/ · horas aprobadas, por aprobar y las que faltan."""

    permission_classes = [TieneRol]
    roles = (Rol.ESTUDIANTE,)

    def get(self, request):
        resumen = horas_services.resumen_horas(request.user)
        return Response({
            "estudiante": request.user.nombre_completo,
            "programa": str(request.user.programa) if request.user.programa else None,
            "meta": resumen["meta"],
            "aprobadas": resumen["aprobadas"],
            "por_aprobar": resumen["por_aprobar"],
            "faltan": resumen["faltan"],
            "porcentaje": resumen["porcentaje"],
            "estado": resumen["estado_texto"],
            "por_tipo": [{"tipo": t["nombre"], "horas": t["horas"]} for t in resumen["por_tipo"]],
        })


class NotificacionesView(generics.ListAPIView):
    """GET /api/notificaciones/ · notificaciones sin leer del usuario."""

    serializer_class = NotificacionSerializer
    permission_classes = [TieneRol]

    def get_queryset(self):
        return self.request.user.notificaciones.filter(leida=False)


class IndicadoresView(APIView):
    """GET /api/dashboard/ · indicadores generales (base del dashboard de la Semana 4)."""

    permission_classes = [TieneRol]
    roles = (Rol.BIENESTAR, Rol.COORDINADOR, Rol.ADMIN)

    def get(self, request):
        programa = request.user.programa if request.user.es_coordinador else None
        filas = horas_services.seguimiento(programa=programa)
        registros = RegistroHoras.objects.all()
        if programa:
            registros = registros.filter(estudiante__programa=programa)
        return Response({
            "programa": str(programa) if programa else "Todos",
            "estudiantes": len(filas),
            "cumplen_meta": sum(1 for f in filas if f["estado"] == "cumple"),
            "en_riesgo": sum(1 for f in filas if f["estado"] == "en-riesgo"),
            "horas_aprobadas": sum((f["horas"] for f in filas), 0),
            "solicitudes_por_aprobar": registros.filter(estado=RegistroHoras.Estado.POR_APROBAR).count(),
            "actividades_realizadas": Actividad.objects.filter(estado=Actividad.Estado.FINALIZADA).count(),
        })
