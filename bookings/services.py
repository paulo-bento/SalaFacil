from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from rooms.models import Sala

from .models import Reserva


@transaction.atomic
def criar_reserva(*, usuario, sala_id, data, inicio, fim, finalidade):
    if not usuario.is_authenticated or not usuario.is_active:
        raise ValidationError("Usuário não autorizado.")

    agora = timezone.localtime()

    if data < agora.date():
        raise ValidationError("Não é permitido reservar datas passadas.")

    if inicio >= fim:
        raise ValidationError(
            "O horário de término deve ser posterior ao início."
        )

    if inicio < time(7, 0) or fim > time(22, 0):
        raise ValidationError(
            "As reservas devem ocorrer entre 07h e 22h."
        )

    for horario in (inicio, fim):
        if (
            horario.minute not in (0, 30)
            or horario.second != 0
            or horario.microsecond != 0
        ):
            raise ValidationError(
                "Utilize horários em intervalos de 30 minutos."
            )

    if data == agora.date() and inicio <= agora.time():
        raise ValidationError("Não é permitido reservar horários passados.")

    finalidade = finalidade.strip()

    if not finalidade or len(finalidade) > 200:
        raise ValidationError(
            "Informe uma finalidade de até 200 caracteres."
        )

    try:
        sala = Sala.objects.select_for_update().get(pk=sala_id)
    except Sala.DoesNotExist:
        raise ValidationError("Sala não encontrada.")

    if not sala.ativa:
        raise ValidationError("Esta sala não está disponível.")

    existe_conflito = Reserva.objects.filter(
        sala=sala,
        data=data,
        status=Reserva.Status.CONFIRMADA,
        inicio__lt=fim,
        fim__gt=inicio,
    ).exists()

    if existe_conflito:
        raise ValidationError(
            "Esta sala já está reservada no horário selecionado."
        )

    return Reserva.objects.create(
        sala=sala,
        usuario=usuario,
        data=data,
        inicio=inicio,
        fim=fim,
        finalidade=finalidade,
        status=Reserva.Status.CONFIRMADA,
    )


@transaction.atomic
def cancelar_reserva(*, usuario, reserva_id):
    if not usuario.is_authenticated or not usuario.is_active:
        raise ValidationError("Usuário não autorizado.")

    try:
        reserva = (
            Reserva.objects.select_for_update()
            .get(pk=reserva_id)
        )
    except Reserva.DoesNotExist:
        raise ValidationError("Reserva não encontrada.")

    if reserva.usuario_id != usuario.pk:
        raise ValidationError("Você não pode cancelar esta reserva.")

    if reserva.status == Reserva.Status.CANCELADA:
        raise ValidationError("Esta reserva já está cancelada.")

    inicio_reserva = timezone.make_aware(
        datetime.combine(reserva.data, reserva.inicio),
        timezone.get_current_timezone(),
    )

    if inicio_reserva <= timezone.now():
        raise ValidationError(
            "Não é permitido cancelar uma reserva após seu início."
        )

    reserva.status = Reserva.Status.CANCELADA
    reserva.save(update_fields=["status"])

    return reserva
