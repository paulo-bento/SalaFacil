from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")

        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail institucional",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Seu nome"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Seu sobrenome"}),
            "email": forms.EmailInput(attrs={"placeholder": "voce@unifip.edu.br"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está sendo utilizado por outra conta.")
        return email
