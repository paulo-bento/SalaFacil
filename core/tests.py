
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Reserva

from rooms.models import Sala

from datetime import time, timedelta


class FiltroTipoSalaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.usuario = User.objects.create_user(
            email="filtro@unifip.edu.br",
            password="SenhaSegura123!",
        )

        cls.laboratorio = Sala.objects.create(
            nome="Laboratório 01",
            nome_curto="Lab 01",
            tipo="Laboratório",
            localizacao="Bloco A",
            capacidade=30,
        )

        cls.sala_aula = Sala.objects.create(
            nome="Sala 101",
            nome_curto="Sala 101",
            tipo="Sala de aula",
            localizacao="Bloco B",
            capacidade=40,
        )

        cls.sala_inativa = Sala.objects.create(
            nome="Laboratório Inativo",
            nome_curto="Lab Inativo",
            tipo="Laboratório",
            localizacao="Bloco C",
            capacidade=20,
            ativa=False,
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_sem_filtro_exibe_todas_as_salas_ativas(self):
        resposta = self.client.get(reverse("home"))

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(self.laboratorio, resposta.context["salas"])
        self.assertIn(self.sala_aula, resposta.context["salas"])
        self.assertNotIn(self.sala_inativa, resposta.context["salas"])

    def test_filtro_exibe_apenas_tipo_selecionado(self):
        resposta = self.client.get(
            reverse("home"),
            {"tipo": "Laboratório"},
        )

        self.assertEqual(resposta.context["salas"], [self.laboratorio])
        self.assertEqual(
            resposta.context["tipo_selecionado"],
            "Laboratório",
        )

    def test_tipos_disponiveis_sem_duplicacao(self):
        Sala.objects.create(
            nome="Laboratório 02",
            nome_curto="Lab 02",
            tipo="Laboratório",
            localizacao="Bloco D",
            capacidade=25,
        )

        resposta = self.client.get(reverse("home"))

        self.assertEqual(
            resposta.context["tipos_sala"],
            ["Laboratório", "Sala de aula"],
        )

    def test_filtro_inexistente_retorna_lista_vazia(self):
        resposta = self.client.get(
            reverse("home"),
            {"tipo": "Auditório"},
        )

        self.assertEqual(resposta.context["salas"], [])
        self.assertEqual(resposta.context["grade"], [])

    def test_filtro_preserva_data_da_agenda(self):
        resposta = self.client.get(
            reverse("home"),
            {
                "tipo": "Laboratório",
                "data": "2026-11-05",
            },
        )

        self.assertEqual(
            resposta.context["data_agenda"].isoformat(),
            "2026-11-05",
        )
        self.assertEqual(resposta.context["salas"], [self.laboratorio])



class DetalhesReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.usuario = User.objects.create_user(
            email="detalhes@unifip.edu.br",
            password="SenhaSegura123!",
        )
        cls.outro_usuario = User.objects.create_user(
            email="outro.detalhes@unifip.edu.br",
            password="SenhaSegura123!",
        )
        cls.sala = Sala.objects.create(
            nome="Laboratório de Testes",
            nome_curto="Lab Teste",
            tipo="Laboratório",
            localizacao="Bloco A",
            capacidade=30,
        )

        cls.data_reserva = timezone.localdate() + timedelta(days=1)

    def setUp(self):
        self.client.force_login(self.usuario)

    def criar_reserva(self, *, usuario=None, status=Reserva.Status.CONFIRMADA):
        return Reserva.objects.create(
            sala=self.sala,
            usuario=usuario or self.usuario,
            data=self.data_reserva,
            inicio=time(9, 0),
            fim=time(10, 0),
            finalidade="Aula de programação",
            status=status,
        )

    def obter_intervalo(self):
        resposta = self.client.get(
            reverse("home"),
            {"data": self.data_reserva.isoformat()},
        )

        self.assertEqual(resposta.status_code, 200)

        grade = resposta.context["grade"]
        sala_grade = next(
            item for item in grade
            if item["sala"].pk == self.sala.pk
        )

        return next(
            intervalo for intervalo in sala_grade["intervalos"]
            if intervalo["hora"] == "09:00"
        )

    def test_reserva_confirmada_aparece_ocupada(self):
        reserva = self.criar_reserva()

        intervalo = self.obter_intervalo()

        self.assertTrue(intervalo["ocupado"])
        self.assertEqual(intervalo["reserva"].pk, reserva.pk)

    def test_reserva_propria_eh_identificada(self):
        self.criar_reserva()

        intervalo = self.obter_intervalo()

        self.assertTrue(intervalo["minha_reserva"])

    def test_reserva_de_outro_usuario_nao_eh_propria(self):
        self.criar_reserva(usuario=self.outro_usuario)

        intervalo = self.obter_intervalo()

        self.assertTrue(intervalo["ocupado"])
        self.assertFalse(intervalo["minha_reserva"])

    def test_finalidade_de_outro_usuario_nao_aparece_no_html(self):
        self.criar_reserva(usuario=self.outro_usuario)

        resposta = self.client.get(
            reverse("home"),
            {"data": self.data_reserva.isoformat()},
        )

        self.assertNotContains(
            resposta,
            'data-finalidade="Aula de programação"',
        )

    def test_reserva_cancelada_nao_ocupa_horario(self):
        self.criar_reserva(status=Reserva.Status.CANCELADA)

        intervalo = self.obter_intervalo()

        self.assertFalse(intervalo["ocupado"])
        self.assertIsNone(intervalo["reserva"])
