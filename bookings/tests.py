from datetime import time, timedelta

import json

from django.urls import reverse

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from rooms.models import Sala

from .models import Reserva
from .services import criar_reserva


class ReservaServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            email="teste@gmail.com",
            password="SenhaDeTeste123!",
        )

        cls.sala = Sala.objects.create(
            nome="Laboratório Teste",
            nome_curto="Lab. Teste",
            tipo="Informática",
            localizacao="Bloco A",
            capacidade=30,
        )

        cls.outra_sala = Sala.objects.create(
            nome="Sala Teste 02",
            nome_curto="Sala 02",
            tipo="Sala de aula",
            localizacao="Bloco B",
            capacidade=20,
        )

    def setUp(self):
        self.data = timezone.localdate() + timedelta(days=1)

    def reservar(self, **alteracoes):
        dados = {
            "usuario": self.usuario,
            "sala_id": self.sala.pk,
            "data": self.data,
            "inicio": time(9, 0),
            "fim": time(10, 0),
            "finalidade": "Aula de informática",
        }

        dados.update(alteracoes)
        return criar_reserva(**dados)

    def test_criar_reserva_valida(self):
        reserva = self.reservar()

        self.assertEqual(
            reserva.status,
            Reserva.Status.CONFIRMADA,
        )
        self.assertEqual(Reserva.objects.count(), 1)

    def test_impedir_conflito(self):
        self.reservar()

        with self.assertRaises(ValidationError):
            self.reservar(
                inicio=time(9, 30),
                fim=time(10, 30),
            )

        self.assertEqual(Reserva.objects.count(), 1)

    def test_permitir_horario_seguinte(self):
        self.reservar()

        self.reservar(
            inicio=time(10, 0),
            fim=time(11, 0),
        )

        self.assertEqual(Reserva.objects.count(), 2)

    def test_permitir_outra_sala(self):
        self.reservar()

        self.reservar(sala_id=self.outra_sala.pk)

        self.assertEqual(Reserva.objects.count(), 2)

    def test_reserva_cancelada_nao_bloqueia(self):
        reserva = self.reservar()
        reserva.status = Reserva.Status.CANCELADA
        reserva.save(update_fields=["status"])

        self.reservar()

        self.assertEqual(Reserva.objects.count(), 2)

    def test_impedir_horario_invalido(self):
        with self.assertRaises(ValidationError):
            self.reservar(
                inicio=time(10, 0),
                fim=time(9, 0),
            )

    def test_impedir_fora_do_expediente(self):
        with self.assertRaises(ValidationError):
            self.reservar(inicio=time(6, 30))

        with self.assertRaises(ValidationError):
            self.reservar(
                inicio=time(21, 30),
                fim=time(22, 30),
            )

    def test_impedir_intervalo_irregular(self):
        with self.assertRaises(ValidationError):
            self.reservar(inicio=time(9, 15))

    def test_impedir_data_passada(self):
        ontem = timezone.localdate() - timedelta(days=1)

        with self.assertRaises(ValidationError):
            self.reservar(data=ontem)

    def test_impedir_sala_inativa(self):
        self.sala.ativa = False
        self.sala.save(update_fields=["ativa"])

        with self.assertRaises(ValidationError):
            self.reservar()


class CriarReservaHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            email="http-teste@gmail.com",
            password="SenhaDeTeste123!",
        )

        cls.sala = Sala.objects.create(
            nome="Sala HTTP Teste",
            nome_curto="HTTP Teste",
            tipo="Laboratório",
            localizacao="Bloco A",
            capacidade=20,
        )

    def setUp(self):
        self.url = reverse("bookings:criar_reserva")
        self.client.force_login(self.usuario)

        self.dados = {
            "sala_id": self.sala.pk,
            "data": (
                timezone.localdate() + timedelta(days=1)
            ).isoformat(),
            "inicio": "09:00",
            "fim": "10:00",
            "finalidade": "Aula de programação",
        }

    def enviar(self, dados=None):
        return self.client.post(
            self.url,
            data=json.dumps(
                self.dados if dados is None else dados
            ),
            content_type="application/json",
        )

    def test_criar_reserva_http(self):
        resposta = self.enviar()

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(Reserva.objects.count(), 1)

        reserva = Reserva.objects.get()
        self.assertEqual(reserva.usuario, self.usuario)

    def test_conflito_http(self):
        self.enviar()
        resposta = self.enviar()

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 1)

    def test_exigir_autenticacao(self):
        self.client.logout()
        resposta = self.enviar()

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_dados_invalidos(self):
        dados = self.dados.copy()
        dados["inicio"] = "horario-invalido"

        resposta = self.enviar(dados)

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_exigir_post(self):
        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, 405)
