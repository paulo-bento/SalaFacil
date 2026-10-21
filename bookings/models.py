from django.conf import settings
from django.db import models

from rooms.models import Sala


class Reserva(models.Model):
    class Status(models.TextChoices):
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"

    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name="reservas",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas",
    )

    data = models.DateField()

    inicio = models.TimeField()
    fim = models.TimeField()

    finalidade = models.CharField(max_length=200)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CONFIRMADA,
    )

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data", "inicio"]
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(fim__gt=models.F("inicio")),
                name="reserva_fim_apos_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.sala.nome} - {self.data} ({self.inicio} às {self.fim})"
