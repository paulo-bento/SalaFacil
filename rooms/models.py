from django.core.validators import MinValueValidator
from django.db import models


class Sala(models.Model):
    nome = models.CharField(max_length=100)
    nome_curto = models.CharField(max_length=30)
    tipo = models.CharField(max_length=50)
    localizacao = models.CharField(max_length=150)
    capacidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    recursos = models.CharField(max_length=200, blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Sala"
        verbose_name_plural = "Salas"

    def __str__(self):
        return self.nome
