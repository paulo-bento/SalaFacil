import uuid

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .forms import RegistrationForm
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    context = {}

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")

        context["error"] = "E-mail ou senha inválidos."
        context["email"] = email


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
        data = request.POST.copy()
        email = data.get("email", "").strip().lower()
        ja_existe = User.objects.filter(email__iexact=email).exists()

        # se o e-mail já existe, valida o resto com um e-mail "fake"
        # pra resposta ser igual e não revelar quem tem conta
        if ja_existe:
            data["email"] = uuid.uuid4().hex + "@gmail.com"

        form = RegistrationForm(data)

        if form.is_valid():
            if ja_existe:
                send_mail(
                    "SalaFácil - você já tem conta",
                    "Alguém tentou criar uma conta com este e-mail, mas ele já está "
                    "cadastrado. Se foi você, recupere a senha em:\n"
                    + request.build_absolute_uri(reverse("password_reset")),
                    None,
                    [email],
                )
            else:
                form.save()
            return redirect("login")

        if ja_existe:
            form.data = request.POST
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
