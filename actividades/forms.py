from django import forms
from django.utils import timezone

from usuarios.forms import BootstrapFormMixin

from .models import Actividad

FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M"


class ActividadForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["nombre", "tipo", "lugar", "fecha_inicio", "fecha_fin", "cupo", "horas_otorga", "descripcion"]
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=FORMATO_FECHA_HORA),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=FORMATO_FECHA_HORA),
            "cupo": forms.NumberInput(attrs={"min": 1}),
            "horas_otorga": forms.NumberInput(attrs={"min": "0.5", "step": "0.5"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "cupo": "Mínimo 1 estudiante.",
            "horas_otorga": "Debe ser mayor que 0.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("fecha_inicio", "fecha_fin"):
            self.fields[campo].input_formats = [FORMATO_FECHA_HORA]

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("fecha_inicio"), datos.get("fecha_fin")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la de inicio.")
        if inicio and inicio <= timezone.now() and "fecha_inicio" in self.changed_data:
            self.add_error("fecha_inicio", "La actividad debe empezar en una fecha futura.")

        if self.instance.pk:
            ocupados = self.instance.cupos_ocupados
            cupo = datos.get("cupo")
            if cupo is not None and cupo < ocupados:
                self.add_error("cupo", f"Ya hay {ocupados} inscritos: el cupo no puede ser menor.")
            if ocupados and "horas_otorga" in self.changed_data:
                self.add_error("horas_otorga", "No se pueden cambiar las horas: ya hay estudiantes inscritos.")
        return datos
