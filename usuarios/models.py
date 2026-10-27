from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Programa(models.Model):
    """Programa académico y la meta de horas que exige para el grado."""

    id = models.BigAutoField(primary_key=True, db_column="id_programa")
    nombre = models.CharField(max_length=100, unique=True)
    meta_horas = models.PositiveSmallIntegerField(
        "meta de horas", validators=[MinValueValidator(1)]
    )

    class Meta:
        db_table = "programa"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, correo, password=None, **campos):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(correo=self.normalize_email(correo).lower(), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, password=None, **campos):
        campos.setdefault("rol", Usuario.Rol.ADMIN)
        campos.setdefault("is_superuser", True)
        return self.create_user(correo, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema. Inicia sesión con su correo institucional."""

    class Rol(models.TextChoices):
        ESTUDIANTE = "estudiante", "Estudiante"
        LIDER = "lider", "Líder de actividad"
        BIENESTAR = "bienestar", "Bienestar universitario"
        COORDINADOR = "coordinador", "Coordinador de programa"
        ADMIN = "administrador", "Administrador"

    id = models.BigAutoField(primary_key=True, db_column="id_usuario")
    codigo = models.CharField("código", max_length=15, unique=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    correo = models.EmailField("correo institucional", max_length=120, unique=True)
    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.ESTUDIANTE)
    programa = models.ForeignKey(
        Programa, on_delete=models.PROTECT, null=True, blank=True,
        db_column="id_programa", related_name="usuarios",
    )
    semestre = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    is_active = models.BooleanField("activo", default=True, db_column="activo")

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["codigo", "nombres", "apellidos"]

    class Meta:
        db_table = "usuario"
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.codigo})"

    def clean(self):
        super().clean()
        if self.rol in (self.Rol.ESTUDIANTE, self.Rol.COORDINADOR) and not self.programa_id:
            raise ValidationError({"programa": "Los estudiantes y coordinadores deben tener programa."})
        if self.rol == self.Rol.ESTUDIANTE and not self.semestre:
            raise ValidationError({"semestre": "Indica el semestre del estudiante."})
        if self.rol != self.Rol.ESTUDIANTE:
            self.semestre = None

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def is_staff(self):
        """Solo el administrador entra al panel /admin/ de Django."""
        return self.is_superuser or self.rol == self.Rol.ADMIN

    @property
    def es_estudiante(self):
        return self.rol == self.Rol.ESTUDIANTE

    @property
    def es_lider(self):
        return self.rol == self.Rol.LIDER

    @property
    def es_bienestar(self):
        return self.rol == self.Rol.BIENESTAR

    @property
    def es_coordinador(self):
        return self.rol == self.Rol.COORDINADOR

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN
