from django.conf import settings
from django.db import models
from django.db.models import Q

from actividades.models import Inscripcion, TipoActividad


class RegistroHoras(models.Model):
    """Horas de un estudiante. Nacen 'por aprobar' y solo suman si se aprueban.

    Si viene de una inscripción con asistencia, 'inscripcion' tiene valor.
    Si es una actividad externa, 'inscripcion' es nulo y 'soporte' es obligatorio.
    """

    class Estado(models.TextChoices):
        POR_APROBAR = "por_aprobar", "Por aprobar"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    id = models.BigAutoField(primary_key=True, db_column="id_registro")
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        db_column="id_estudiante", related_name="registros_horas",
    )
    inscripcion = models.OneToOneField(
        Inscripcion, on_delete=models.PROTECT, null=True, blank=True,
        db_column="id_inscripcion", related_name="registro_horas",
    )
    nombre_actividad = models.CharField("actividad", max_length=150)
    tipo = models.ForeignKey(
        TipoActividad, on_delete=models.PROTECT, db_column="id_tipo", related_name="registros_horas"
    )
    fecha_actividad = models.DateField("fecha de la actividad")
    horas = models.DecimalField(max_digits=4, decimal_places=1)
    soporte = models.FileField(upload_to="soportes/%Y/%m/", max_length=255, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.POR_APROBAR)
    motivo = models.TextField(blank=True)
    aprobador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        db_column="id_aprobador", related_name="registros_revisados",
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "registro_horas"
        ordering = ["-fecha_solicitud"]
        verbose_name = "registro de horas"
        verbose_name_plural = "registros de horas"
        constraints = [
            models.CheckConstraint(condition=Q(horas__gt=0), name="registro_horas_positivas"),
        ]

    def __str__(self):
        return f"{self.estudiante} · {self.nombre_actividad} · {self.horas} h"

    @property
    def es_externa(self):
        return self.inscripcion_id is None


class Constancia(models.Model):
    """Constancia en PDF de las horas aprobadas (se genera en la Semana 4)."""

    id = models.BigAutoField(primary_key=True, db_column="id_constancia")
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        db_column="id_estudiante", related_name="constancias",
    )
    codigo_verificacion = models.CharField("código de verificación", max_length=20, unique=True)
    total_horas = models.DecimalField(max_digits=5, decimal_places=1)
    fecha_expedicion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "constancia"
        ordering = ["-fecha_expedicion"]

    def __str__(self):
        return self.codigo_verificacion
