
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rooms.models import Sala


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
