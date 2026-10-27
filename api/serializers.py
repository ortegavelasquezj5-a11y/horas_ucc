from rest_framework import serializers

from actividades import services
from actividades.models import Actividad, Inscripcion
from notificaciones.models import Notificacion


class ActividadSerializer(serializers.ModelSerializer):
    tipo = serializers.StringRelatedField()
    responsable = serializers.CharField(source="responsable.nombre_completo")
    cupos_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Actividad
        fields = ["id", "nombre", "tipo", "lugar", "fecha_inicio", "fecha_fin",
                  "horas_otorga", "cupo", "cupos_disponibles", "responsable"]

    def get_cupos_disponibles(self, actividad):
        ocupados = getattr(actividad, "ocupados", None)
        if ocupados is None:
            return actividad.cupos_disponibles
        return max(actividad.cupo - ocupados, 0)


class InscripcionSerializer(serializers.ModelSerializer):
    actividad = serializers.PrimaryKeyRelatedField(queryset=Actividad.objects.all())

    class Meta:
        model = Inscripcion
        fields = ["id", "actividad", "estado", "fecha_inscripcion"]
        read_only_fields = ["id", "estado", "fecha_inscripcion"]
        validators = []  # duplicados y cupos los valida la capa de servicios

    def create(self, datos):
        try:
            return services.inscribir(self.context["request"].user, datos["actividad"])
        except services.ReglaDeNegocioError as error:
            raise serializers.ValidationError({"detalle": str(error)})


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ["id", "mensaje", "leida", "fecha"]
