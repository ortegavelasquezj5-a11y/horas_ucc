from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class TipoActividad(models.Model):
    """Académica, Investigativa, Cultural, Deportiva o Bienestar."""

    id = models.BigAutoField(primary_key=True, db_column="id_tipo")
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tipo_actividad"
        ordering = ["nombre"]
        verbose_name = "tipo de actividad"
        verbose_name_plural = "tipos de actividad"

    def __str__(self):
        return self.nombre


class Actividad(models.Model):
    """Actividad o evento que otorga horas a quienes asisten."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PUBLICADA = "publicada", "Publicada"
        FINALIZADA = "finalizada", "Finalizada"
        CANCELADA = "cancelada", "Cancelada"

    id = models.BigAutoField(primary_key=True, db_column="id_actividad")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField("descripción", blank=True)
    tipo = models.ForeignKey(
        TipoActividad, on_delete=models.PROTECT, db_column="id_tipo", related_name="actividades"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        db_column="id_responsable", related_name="actividades_a_cargo",
    )
    lugar = models.CharField(max_length=120)
    fecha_inicio = models.DateTimeField("inicio")
    fecha_fin = models.DateTimeField("fin")
    cupo = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    horas_otorga = models.DecimalField(
        "horas que otorga", max_digits=4, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.5"))],
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)

    class Meta:
        db_table = "actividad"
        ordering = ["fecha_inicio"]
        verbose_name_plural = "actividades"
        constraints = [
            models.CheckConstraint(condition=Q(fecha_fin__gte=F("fecha_inicio")), name="actividad_fechas_validas"),
            models.CheckConstraint(condition=Q(cupo__gte=1), name="actividad_cupo_minimo"),
            models.CheckConstraint(condition=Q(horas_otorga__gt=0), name="actividad_horas_positivas"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def inscritos(self):
        return self.inscripciones.filter(estado=Inscripcion.Estado.INSCRITO)

    @property
    def cupos_ocupados(self):
        return self.inscritos.count()

    @property
    def cupos_disponibles(self):
        return max(self.cupo - self.cupos_ocupados, 0)

    @property
    def ya_empezo(self):
        return self.fecha_inicio <= timezone.now()


class Inscripcion(models.Model):
    """Un estudiante inscrito en una actividad. 'asistio' lo marca el líder."""

    class Estado(models.TextChoices):
        INSCRITO = "inscrito", "Inscrito"
        CANCELADO = "cancelado", "Cancelado"

    id = models.BigAutoField(primary_key=True, db_column="id_inscripcion")
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        db_column="id_estudiante", related_name="inscripciones",
    )
    actividad = models.ForeignKey(
        Actividad, on_delete=models.PROTECT, db_column="id_actividad", related_name="inscripciones"
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.INSCRITO)
    asistio = models.BooleanField("asistió", null=True, blank=True)

    class Meta:
        db_table = "inscripcion"
        ordering = ["estudiante__apellidos", "estudiante__nombres"]
        verbose_name = "inscripción"
        verbose_name_plural = "inscripciones"
        constraints = [
            models.UniqueConstraint(fields=["estudiante", "actividad"], name="inscripcion_unica"),
        ]

    def __str__(self):
        return f"{self.estudiante} en {self.actividad}"
