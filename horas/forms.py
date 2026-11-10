from django import forms
from django.utils import timezone

from actividades.models import TipoActividad
from usuarios.forms import BootstrapFormMixin


class SoporteForm(BootstrapFormMixin, forms.Form):
    """Solicitud de horas de una actividad externa."""

    nombre_actividad = forms.CharField(label="Nombre de la actividad", max_length=150)
    tipo = forms.ModelChoiceField(label="Tipo", queryset=TipoActividad.objects.all())
    fecha_actividad = forms.DateField(
        label="Fecha", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )
    horas = forms.DecimalField(
        label="Horas solicitadas", min_value=0.5, max_value=40, decimal_places=1, max_digits=4,
        widget=forms.NumberInput(attrs={"step": "0.5", "min": "0.5", "max": "40"}),
    )
    soporte = forms.FileField(
        label="Soporte (certificado o constancia)",
        help_text="PDF, JPG o PNG · máximo 5 MB. Debe mostrar tu nombre, la fecha y la intensidad horaria.",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png", "data-max-mb": "5"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El navegador también bloquea fechas futuras (validación en el cliente)
        self.fields["fecha_actividad"].widget.attrs["max"] = timezone.localdate().isoformat()

    def clean_fecha_actividad(self):
        fecha = self.cleaned_data["fecha_actividad"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser futura.")
        return fecha


class RevisionForm(BootstrapFormMixin, forms.Form):
    """Bienestar aprueba (opcionalmente ajustando las horas) o rechaza."""

    accion = forms.ChoiceField(choices=[("aprobar", "Aprobar"), ("rechazar", "Rechazar")], widget=forms.HiddenInput)
    horas = forms.DecimalField(
        label="Horas a aprobar", required=False, min_value=0.5, max_value=40,
        decimal_places=1, max_digits=4, widget=forms.NumberInput(attrs={"step": "0.5"}),
    )
    motivo = forms.CharField(
        label="Motivo (obligatorio para rechazar o ajustar las horas)", required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: el soporte no indica la intensidad horaria"}),
    )
