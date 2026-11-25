from django.contrib import admin

from .models import Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "tipo",
        "localizacao",
        "capacidade",
        "permite_reserva_aluno",
        "ativa",
    )
    list_filter = ("ativa", "tipo", "permite_reserva_aluno")
    search_fields = ("nome", "localizacao")
