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

    salas_query = Sala.objects.filter(ativa=True)

    tipos_sala = list(
        salas_query.order_by("tipo")
        .values_list("tipo", flat=True)
        .distinct()
    )

    tipo_selecionado = request.GET.get("tipo", "")

    if tipo_selecionado:
        salas_query = salas_query.filter(tipo=tipo_selecionado)

    salas = list(salas_query)


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
            reserva_intervalo = next(
                (
                    reserva
                    for reserva in reservas_por_sala[sala.pk]
                    if reserva.inicio <= horario < reserva.fim
                ),
                None,
            )

            intervalos.append({
                "hora": horario.strftime("%H:%M"),
                "ocupado": reserva_intervalo is not None,
                "reserva": reserva_intervalo,
                "minha_reserva": (
                    reserva_intervalo is not None
                    and reserva_intervalo.usuario_id == request.user.pk
                ),
            })


        grade.append({
            "sala": sala,
            "intervalos": intervalos,
        })


    minhas_reservas = (
        Reserva.objects.filter(usuario=request.user)
        .select_related("sala")
        .order_by("-data", "-inicio")
    )

    agora = timezone.localtime()

    for reserva in minhas_reservas:
        reserva.pode_cancelar = (
            reserva.status == Reserva.Status.CONFIRMADA
            and (
                reserva.data > agora.date()
                or (
                    reserva.data == agora.date()
                    and reserva.inicio > agora.time()
                )
            )
        )


    return render(request, "core/dashboard.html", {
        "salas": salas,
        "tipos_sala": tipos_sala,
        "tipo_selecionado": tipo_selecionado,
        "data_agenda": data_agenda,
        "horarios": horarios,
        "grade": grade,
        "minhas_reservas": minhas_reservas,
    })



def agenda_preview(request):
    if not settings.DEBUG:
        raise Http404

    return render(request, "core/agenda_preview.html")
