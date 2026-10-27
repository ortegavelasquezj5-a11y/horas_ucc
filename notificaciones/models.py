from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Aviso dentro de la plataforma para un usuario."""

    id = models.BigAutoField(primary_key=True, db_column="id_notificacion")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        db_column="id_usuario", related_name="notificaciones",
    )
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField("leída", default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notificacion"
        ordering = ["-fecha", "-id"]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"

    def __str__(self):
        return self.mensaje
