
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager
from .validators import validate_institutional_email


class User(AbstractUser):
    class Perfil(models.TextChoices):
        ALUNO = "aluno", "Aluno"
        PROFESSOR = "professor", "Professor"

    username = None
    email = models.EmailField(
        unique=True,
        validators=[validate_institutional_email],
    )
    perfil = models.CharField(
        "perfil acadêmico", max_length=9, choices=Perfil.choices, default=Perfil.ALUNO,
    )
    # Controla os avisos e o contador. O histórico é registrado para todas as contas.
    recebe_notificacoes_reserva = models.BooleanField(
        "recebe notificações de reservas", default=True,
    )
    tipos_sala_preferidos = models.JSONField(
        "tipos de sala preferidos", default=list, blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_user_email_case_insensitive",
            ),
        ]

    def __str__(self) -> str:
        return self.email
