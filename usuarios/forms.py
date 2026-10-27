from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Programa, Usuario


class BootstrapFormMixin:
    """Agrega las clases de Bootstrap 5 a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                clase = "form-check-input"
            elif isinstance(widget, forms.Select):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()

    def full_clean(self):
        """Marca en rojo (is-invalid) los campos con error."""
        super().full_clean()
        for nombre in self.errors:
            if nombre in self.fields:
                widget = self.fields[nombre].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


class UsuarioForm(BootstrapFormMixin, forms.ModelForm):
    """Crear o editar usuarios (solo el administrador)."""

    clave = forms.CharField(
        label="Contraseña", required=False, strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Obligatoria al crear. Al editar, déjala vacía para no cambiarla.",
    )

    class Meta:
        model = Usuario
        fields = ["codigo", "nombres", "apellidos", "correo", "rol", "programa", "semestre"]
        error_messages = {
            "codigo": {"unique": "Ya existe un usuario con este código."},
            "correo": {"unique": "Ya existe un usuario con este correo."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["semestre"].widget.attrs.update(min=1, max=10)
        self.fields["programa"].empty_label = "— Sin programa —"

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()
        if not correo.endswith("@campusucc.edu.co"):
            raise forms.ValidationError("Usa un correo institucional (@campusucc.edu.co).")
        return correo

    def clean(self):
        datos = super().clean()
        clave = datos.get("clave")
        if not self.instance.pk and not clave:
            self.add_error("clave", "Escribe una contraseña inicial.")
        elif clave:
            try:
                validate_password(clave, self.instance)
            except forms.ValidationError as error:
                self.add_error("clave", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("clave"):
            usuario.set_password(self.cleaned_data["clave"])
        if commit:
            usuario.save()
        return usuario


class ProgramaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Programa
        fields = ["nombre", "meta_horas"]
        widgets = {"meta_horas": forms.NumberInput(attrs={"min": 1})}
