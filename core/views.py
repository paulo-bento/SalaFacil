from datetime import date, time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from bookings.models import Reserva
from rooms.models import Sala


@login_required(login_url="login")
def home(request):
    salas = list(Sala.objects.filter(ativa=True))

    data_agenda = timezone.localdate()
    data_parametro = request.GET.get("data")

    if data_parametro:
        try:
            data_agenda = date.fromisoformat(data_parametro)
        except ValueError:
            pass

    horarios_obj = [
        time(hora, minuto)
        for hora in range(7, 22)
        for minuto in (0, 30)
    ]

    horarios = [
        horario.strftime("%H:%M")
        for horario in horarios_obj
    ]

    reservas = Reserva.objects.filter(
        sala__in=salas,
        data=data_agenda,
        status=Reserva.Status.CONFIRMADA,
    )

    reservas_por_sala = {
        sala.pk: []
        for sala in salas
    }

    for reserva in reservas:
        reservas_por_sala[reserva.sala_id].append(reserva)

    grade = []

    for sala in salas:
        intervalos = []

        for horario in horarios_obj:
            ocupado = any(
                reserva.inicio <= horario < reserva.fim
                for reserva in reservas_por_sala[sala.pk]
            )

            intervalos.append({
                "hora": horario.strftime("%H:%M"),
                "ocupado": ocupado,
            })

        grade.append({
            "sala": sala,
            "intervalos": intervalos,
        })

    return render(request, "core/dashboard.html", {
        "salas": salas,
        "data_agenda": data_agenda,
        "horarios": horarios,
        "grade": grade,
    })


def agenda_preview(request):
    if not settings.DEBUG:
        raise Http404

    return render(request, "core/agenda_preview.html")
