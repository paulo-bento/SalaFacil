from datetime import date, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.forms import DadosPessoaisForm, PreferenciasAgendaForm
from bookings.models import NotificacaoReserva, Reserva
from bookings.services import estado_notificacoes, perfil_pode_reservar_sala
from rooms.models import Sala


def _ler_data_iso(valor):
    try:
        return date.fromisoformat(valor or "")
    except ValueError:
        return None


def _render_dashboard(request, contexto):
    return render(request, "core/dashboard.html", {
        **contexto,
        **estado_notificacoes(request.user),
    })


def _tipos_salas_ativas() -> list[str]:
    return list(
        Sala.objects.filter(ativa=True).order_by("tipo")
        .values_list("tipo", flat=True)
        .distinct()
    )


@login_required(login_url="login")
@never_cache
def home(request):

    salas_query = Sala.objects.filter(ativa=True)
    tipos_sala = _tipos_salas_ativas()

    if request.GET.get("limpar_tipos") == "1":
        tipos_selecionados = []
    elif "tipo" in request.GET or request.GET.get("filtro_tipos") == "1":
        tipos_selecionados = list(dict.fromkeys(tipo for tipo in request.GET.getlist("tipo") if tipo))
    else:
        tipos_preferidos = request.user.tipos_sala_preferidos
        tipos_selecionados = [tipo for tipo in tipos_sala if tipo in tipos_preferidos]

    if tipos_selecionados:
        salas_query = salas_query.filter(tipo__in=tipos_selecionados)

    salas = list(salas_query)
    salas_reservaveis = [sala for sala in salas if perfil_pode_reservar_sala(request.user, sala)]


    cookie_data = f"salafacil_agenda_data_{request.user.pk}"
    data_consultada = _ler_data_iso(request.GET.get("data"))
    data_salva = _ler_data_iso(request.COOKIES.get(cookie_data))
    data_agenda = data_consultada or data_salva or timezone.localdate()

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
    ).select_related("usuario")

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

            matiz_reserva = (
                (reserva_intervalo.pk * 13751) % 36000 / 100
                if reserva_intervalo is not None else None
            )
            intervalos.append({
                "hora": horario.strftime("%H:%M"),
                "ocupado": reserva_intervalo is not None,
                "reserva": reserva_intervalo,
                "matiz_reserva": matiz_reserva,
                "minha_reserva": (
                    reserva_intervalo is not None
                    and reserva_intervalo.usuario_id == request.user.pk
                ),
            })


        grade.append({
            "sala": sala,
            "intervalos": intervalos,
        })


    resposta = _render_dashboard(request, {
        "titulo_pagina": "Agenda de salas",
        "pagina_atual": "agenda",
        "salas": salas,
        "salas_reservaveis": salas_reservaveis,
        "tipos_sala": tipos_sala,
        "tipos_selecionados": tipos_selecionados,
        "data_agenda": data_agenda,
        "horarios": horarios,
        "grade": grade,
    })
    if data_consultada is not None:
        resposta.set_cookie(
            cookie_data,
            data_consultada.isoformat(),
            max_age=timedelta(days=365),
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
        )
    return resposta


@login_required(login_url="login")
def minhas_reservas(request):
    reservas = (
        Reserva.objects.filter(usuario=request.user)
        .select_related("sala")
        .order_by("-data", "-inicio", "-pk")
    )
    minhas_reservas = Paginator(reservas, 15).get_page(request.GET.get("pagina"))

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


    return _render_dashboard(request, {
        "titulo_pagina": "Minhas reservas",
        "pagina_atual": "reservas",
        "minhas_reservas": minhas_reservas,
    })


@login_required(login_url="login")
@never_cache
def notificacoes(request):
    historico = NotificacaoReserva.objects.filter(
        reserva__usuario=request.user,
    ).select_related("reserva__sala")
    pagina = Paginator(historico, 10).get_page(request.GET.get("pagina"))

    if request.GET.get("fragmento") == "lista":
        return render(request, "core/notificacoes.html", {
            "notificacoes": pagina,
            **estado_notificacoes(request.user),
        })

    return _render_dashboard(request, {
        "titulo_pagina": "Notificações",
        "pagina_atual": "notificacoes",
        "notificacoes": pagina,
    })


@login_required(login_url="login")
@never_cache
@require_http_methods(["GET", "POST"])
def configuracoes(request: HttpRequest) -> HttpResponse:
    acao = request.POST.get("acao")
    if request.method == "POST" and acao not in ("dados_pessoais", "preferencias_agenda"):
        return HttpResponseBadRequest("Ação inválida.")

    dados_pessoais = DadosPessoaisForm(
        request.POST if acao == "dados_pessoais" else None, instance=request.user,
    )
    preferencias_agenda = PreferenciasAgendaForm(
        request.POST if acao == "preferencias_agenda" else None,
        instance=request.user, tipos_sala=_tipos_salas_ativas(),
    )

    if dados_pessoais.is_bound and dados_pessoais.is_valid():
        usuario = dados_pessoais.save(commit=False)
        usuario.save(update_fields=["first_name", "last_name"])
        messages.success(request, "Dados pessoais atualizados.")
        return redirect(reverse("configuracoes") + "#dados-pessoais")

    if preferencias_agenda.is_bound and preferencias_agenda.is_valid():
        usuario = preferencias_agenda.save(commit=False)
        usuario.save(update_fields=["tipos_sala_preferidos"])
        messages.success(request, "Preferências da agenda salvas.")
        return redirect(reverse("configuracoes") + "#preferencias-agenda")

    return _render_dashboard(request, {
        "titulo_pagina": "Configurações",
        "pagina_atual": "configuracoes",
        "dados_pessoais": dados_pessoais,
        "preferencias_agenda": preferencias_agenda,
    })


def _resposta_leitura(request, mensagem):
    if request.headers.get("Accept") == "application/json":
        estado = estado_notificacoes(request.user)
        return JsonResponse({
            "lida": True,
            "tem_nao_lidas": estado["notificacoes_nao_lidas"] > 0,
            **estado,
        })

    messages.success(request, mensagem)
    return redirect("notificacoes")


@login_required(login_url="login")
@never_cache
@require_GET
def consultar_estado_notificacoes(request):
    return JsonResponse(estado_notificacoes(request.user))


@login_required(login_url="login")
@require_POST
def salvar_preferencia_notificacoes(request):
    valor = request.POST.get("receber")
    if valor not in ("0", "1"):
        return HttpResponseBadRequest("Preferência inválida.")

    recebe = valor == "1"
    request.user.recebe_notificacoes_reserva = recebe
    request.user.save(update_fields=["recebe_notificacoes_reserva"])

    if request.headers.get("Accept") == "application/json":
        return JsonResponse(estado_notificacoes(request.user))

    messages.success(request, "Preferência salva.")
    return redirect("configuracoes")


@login_required(login_url="login")
@require_POST
def ler_notificacao(request, notificacao_id):
    historico = NotificacaoReserva.objects.filter(reserva__usuario=request.user)
    atualizadas = historico.filter(pk=notificacao_id).update(lida=True)
    if not atualizadas:
        raise Http404

    return _resposta_leitura(request, "Notificação marcada como lida.")


@login_required(login_url="login")
@require_POST
def ler_todas_notificacoes(request):
    historico = NotificacaoReserva.objects.filter(reserva__usuario=request.user)
    historico.filter(lida=False).update(lida=True)
    return _resposta_leitura(request, "Todas as notificações foram marcadas como lidas.")


def agenda_preview(request):
    if not settings.DEBUG:
        raise Http404

    return render(request, "core/agenda_preview.html")
