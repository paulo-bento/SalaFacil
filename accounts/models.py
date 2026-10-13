
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager
from .validators import validate_institutional_email


class User(AbstractUser):
    username = None
    email = models.EmailField(
        unique=True,
        validators=[validate_institutional_email],
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
