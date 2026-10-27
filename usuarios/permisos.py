"""Control de acceso según el rol del usuario."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import Usuario

Rol = Usuario.Rol


class RolRequeridoMixin(LoginRequiredMixin):
    """Exige sesión iniciada y que el rol del usuario esté en `roles`.

    Sin sesión → redirige al login. Con sesión pero sin permiso → error 403.
    """

    roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.roles and request.user.rol not in self.roles:
            raise PermissionDenied("Tu rol no tiene acceso a esta página.")
        return super().dispatch(request, *args, **kwargs)


class EstudianteMixin(RolRequeridoMixin):
    roles = (Rol.ESTUDIANTE,)


class GestorActividadesMixin(RolRequeridoMixin):
    """Quienes crean actividades y registran asistencia."""

    roles = (Rol.LIDER, Rol.BIENESTAR, Rol.ADMIN)


class BienestarMixin(RolRequeridoMixin):
    roles = (Rol.BIENESTAR, Rol.ADMIN)


class SeguimientoMixin(RolRequeridoMixin):
    roles = (Rol.COORDINADOR, Rol.BIENESTAR, Rol.ADMIN)


class AdminMixin(RolRequeridoMixin):
    roles = (Rol.ADMIN,)
