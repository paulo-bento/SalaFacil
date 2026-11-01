
from django.urls import path

from . import views


app_name = "bookings"

urlpatterns = [
    path(
        "criar/",
        views.criar_reserva_view,
        name="criar_reserva",
    ),
    path(
        "cancelar/<int:reserva_id>/",
        views.cancelar_reserva_view,
        name="cancelar_reserva",
    ),
]
