import json
import re
from datetime import date, time

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services import criar_reserva


@require_POST
def criar_reserva_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"erro": "É necessário estar autenticado."},
            status=401,
        )

    if request.content_type != "application/json":
        return JsonResponse(
            {"erro": "Envie os dados em formato JSON."},
            status=415,
        )

    try:
        dados = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"erro": "JSON inválido."},
            status=400,
        )

    if not isinstance(dados, dict):
        return JsonResponse(
            {"erro": "Os dados enviados são inválidos."},
            status=400,
        )

    try:
        sala_id = dados["sala_id"]
        data_texto = dados["data"]
        inicio_texto = dados["inicio"]
        fim_texto = dados["fim"]
        finalidade = dados["finalidade"]

        if (
            isinstance(sala_id, bool)
            or not isinstance(sala_id, int)
            or sala_id < 1
            or not all(
                isinstance(valor, str)
                for valor in (
                    data_texto,
                    inicio_texto,
                    fim_texto,
                    finalidade,
                )
            )
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data_texto)
            or not re.fullmatch(r"\d{2}:\d{2}", inicio_texto)
            or not re.fullmatch(r"\d{2}:\d{2}", fim_texto)
        ):
            raise ValueError

        data = date.fromisoformat(data_texto)
        inicio = time.fromisoformat(inicio_texto)
        fim = time.fromisoformat(fim_texto)

    except (KeyError, TypeError, ValueError):
        return JsonResponse(
            {"erro": "Verifique os dados da reserva."},
            status=400,
        )

    try:
        reserva = criar_reserva(
            usuario=request.user,
            sala_id=sala_id,
            data=data,
            inicio=inicio,
            fim=fim,
            finalidade=finalidade,
        )

    except ValidationError as erro:
        return JsonResponse(
            {"erro": " ".join(erro.messages)},
            status=400,
        )

    return JsonResponse(
        {
            "mensagem": "Reserva confirmada com sucesso.",
            "reserva_id": reserva.pk,
        },
        status=201,
    )
