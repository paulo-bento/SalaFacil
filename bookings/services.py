from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from accounts.models import User
from rooms.models import Sala

from .models import NotificacaoReserva, Reserva


def estado_notificacoes(usuario):
    estado = NotificacaoReserva.objects.filter(reserva__usuario=usuario).aggregate(
        notificacoes_nao_lidas=Count("pk", filter=Q(lida=False)),
        ultima_notificacao_id=Max("pk", default=0),
    )
    return {**estado, "avisos_notificacoes_ativos": usuario.recebe_notificacoes_reserva}


def perfil_pode_reservar_sala(usuario, sala):
    return usuario.perfil == User.Perfil.PROFESSOR or (
        usuario.perfil == User.Perfil.ALUNO and sala.permite_reserva_aluno
    )


@transaction.atomic
def criar_reserva(*, usuario, sala_id, data, inicio, fim, finalidade):
    if not usuario.is_authenticated or not usuario.is_active:
        raise ValidationError("Usuário não autorizado.")

    agora = timezone.localtime()

    if data < agora.date():
        raise ValidationError("Não é permitido reservar datas passadas.", code="data")

    if inicio >= fim:
        raise ValidationError(
            "O horário de término deve ser posterior ao início.", code="fim",
        )

    if inicio < time(7, 0) or fim > time(22, 0):
        raise ValidationError(
            "As reservas devem ocorrer entre 07h e 22h.",
            code="inicio" if inicio < time(7, 0) else "fim",
        )

    for campo, horario in (("inicio", inicio), ("fim", fim)):
        if (
            horario.minute not in (0, 30)
            or horario.second != 0
            or horario.microsecond != 0
        ):
            raise ValidationError(
                "Utilize horários em intervalos de 30 minutos.", code=campo,
            )

    if data == agora.date() and inicio <= agora.time():
        raise ValidationError("Não é permitido reservar horários passados.", code="inicio")

    finalidade = finalidade.strip()

    if not finalidade or len(finalidade) > 200:
        raise ValidationError(
            "Informe uma finalidade de até 200 caracteres.", code="finalidade",
        )

    try:
        sala = Sala.objects.select_for_update().get(pk=sala_id)
    except Sala.DoesNotExist:
        raise ValidationError("Sala não encontrada.", code="sala_id")

    if not sala.ativa:
        raise ValidationError("Esta sala não está disponível.", code="sala_id")

    if not perfil_pode_reservar_sala(usuario, sala):
        raise ValidationError("Esta sala é exclusiva para professores.", code="sala_id")

    existe_conflito = Reserva.objects.filter(
        sala=sala,
        data=data,
        status=Reserva.Status.CONFIRMADA,
        inicio__lt=fim,
        fim__gt=inicio,
    ).exists()

    if existe_conflito:
        raise ValidationError(
            "Esta sala já está reservada no horário selecionado.", code="inicio",
        )

    reserva = Reserva.objects.create(
        sala=sala,
        usuario=usuario,
        data=data,
        inicio=inicio,
        fim=fim,
        finalidade=finalidade,
        status=Reserva.Status.CONFIRMADA,
    )
    NotificacaoReserva.objects.create(reserva=reserva, tipo=reserva.status)

    return reserva


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
    NotificacaoReserva.objects.create(reserva=reserva, tipo=reserva.status)

    return reserva
