
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        email_attrs = self.fields["email"].widget.attrs
        email_attrs.pop("autofocus", None)
        email_attrs["autocomplete"] = "email"
        self.fields["password2"].label = "Confirmar senha"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")

        return email


class DadosPessoaisForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nome", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Sobrenome", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name")


class PreferenciasAgendaForm(forms.ModelForm):
    todos_tipos = forms.BooleanField(label="Todos", required=False)
    tipos_sala_preferidos = forms.MultipleChoiceField(
        label="Tipos de sala", required=False, widget=forms.CheckboxSelectMultiple,
        error_messages={"invalid_choice": "Um dos tipos selecionados está indisponível."},
    )

    class Meta:
        model = User
        fields = ("tipos_sala_preferidos",)

    def __init__(self, *args, tipos_sala: list[str], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["tipos_sala_preferidos"].choices = [(tipo, tipo) for tipo in tipos_sala]
        tipos_salvos = self.initial.get("tipos_sala_preferidos", [])
        self.initial["todos_tipos"] = not any(tipo in tipos_salvos for tipo in tipos_sala)

    def clean(self) -> dict:
        dados = super().clean()
        if "tipos_sala_preferidos" in dados:
            tipos = [] if dados["todos_tipos"] else dados["tipos_sala_preferidos"]
            dados["tipos_sala_preferidos"] = list(dict.fromkeys(tipos))
        return dados
