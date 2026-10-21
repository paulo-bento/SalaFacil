from django.contrib import admin

from .models import Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "tipo",
        "localizacao",
        "capacidade",
        "ativa",
    )
    list_filter = ("ativa", "tipo")
    search_fields = ("nome", "localizacao")
