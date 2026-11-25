from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from .forms import RegistrationForm
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    context = {"perfis": User.Perfil.choices, "perfil_selecionado": User.Perfil.ALUNO}

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        perfil = request.POST.get("perfil")

        user = authenticate(request, email=email, password=password)

        if user is not None and perfil in User.Perfil.values and user.perfil == perfil:
            login(request, user)
            return redirect("home")

        messages.error(request, "E-mail, senha ou perfil inválidos.")
        context["email"] = email
        if perfil in User.Perfil.values:
            context["perfil_selecionado"] = perfil


    return render(request, "accounts/login.html", context)


@login_required(login_url="login")
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Conta criada com sucesso.")
            return redirect("login")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
