
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import NotificacaoReserva, Reserva
from bookings.services import cancelar_reserva, criar_reserva

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
            permite_reserva_aluno=True,
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
            resposta.context["tipos_selecionados"],
            ["Laboratório"],
        )

    def test_consulta_varios_tipos_na_mesma_data(self):
        outro_tipo = Sala.objects.create(
            nome="Auditório Master", nome_curto="Auditório", tipo="Auditório",
            localizacao="Bloco A", capacidade=120,
        )
        data_agenda = timezone.localdate() + timedelta(days=1)
        for sala in (self.laboratorio, self.sala_aula, self.sala_inativa, outro_tipo):
            Reserva.objects.create(
                sala=sala, usuario=self.usuario, data=data_agenda,
                inicio=time(9), fim=time(10), finalidade="Aula",
            )

        resposta = self.client.get(reverse("home"), {
            "tipo": ["Laboratório", "Sala de aula"],
            "data": data_agenda.isoformat(),
        })

        self.assertEqual(resposta.context["data_agenda"], data_agenda)
        self.assertEqual(resposta.context["tipos_selecionados"], ["Laboratório", "Sala de aula"])
        self.assertEqual(resposta.context["salas"], [self.laboratorio, self.sala_aula])
        for item in resposta.context["grade"]:
            ocupados = [slot["hora"] for slot in item["intervalos"] if slot["ocupado"]]
            self.assertEqual(ocupados, ["09:00", "09:30"])
        self.assertContains(resposta, 'value="Laboratório" checked')
        self.assertContains(resposta, 'value="Sala de aula" checked')

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

    def test_limpar_filtro_mantem_data_e_exibe_todos_os_tipos_ativos(self):
        resposta = self.client.get(reverse("home"), {
            "tipo": ["Laboratório"], "data": "2026-11-16", "limpar_tipos": "1",
        })

        self.assertEqual(resposta.context["tipos_selecionados"], [])
        self.assertEqual(resposta.context["data_agenda"].isoformat(), "2026-11-16")
        self.assertEqual(resposta.context["salas"], [self.laboratorio, self.sala_aula])

    def test_filtro_inexistente_retorna_lista_vazia(self):
        resposta = self.client.get(
            reverse("home"),
            {"tipo": "Auditório"},
        )

        self.assertEqual(resposta.context["salas"], [])
        self.assertEqual(resposta.context["grade"], [])

    def test_preferencia_da_agenda_persiste_por_conta(self):
        configuracoes = reverse("configuracoes")
        resposta = self.client.post(configuracoes, {
            "acao": "preferencias_agenda",
            "tipos_sala_preferidos": ["Laboratório", "Sala de aula", "Laboratório"],
        })
        self.assertRedirects(resposta, configuracoes + "#preferencias-agenda")
        self.client.post(reverse("logout"))
        self.client = Client()
        self.client.force_login(self.usuario)
        self.assertEqual(
            self.client.get(reverse("home")).context["tipos_selecionados"],
            ["Laboratório", "Sala de aula"],
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.tipos_sala_preferidos, ["Laboratório", "Sala de aula"])
        outro_usuario = get_user_model().objects.create_user(
            email="sem-preferencia@unifip.edu.br", password="SenhaSegura123!",
        )
        self.client.force_login(outro_usuario)
        self.assertEqual(self.client.get(reverse("home")).context["tipos_selecionados"], [])

    def test_consultas_pontuais_respeitam_data_e_preservam_preferencia(self):
        home = reverse("home")
        self.usuario.tipos_sala_preferidos = ["Laboratório"]
        self.usuario.save(update_fields=["tipos_sala_preferidos"])
        data = "2026-11-16"
        padrao = self.client.get(home, {"data": data})
        self.assertEqual(padrao.context["salas"], [self.laboratorio])
        for params, salas in (
            ({"tipo": "Sala de aula"}, [self.sala_aula]),
            ({"filtro_tipos": "1"}, [self.laboratorio, self.sala_aula]),
            ({"limpar_tipos": "1"}, [self.laboratorio, self.sala_aula]),
        ):
            with self.subTest(params=params):
                resposta = self.client.get(home, {"data": data, **params})
                self.assertEqual(resposta.context["salas"], salas)
                self.assertEqual(resposta.context["data_agenda"].isoformat(), data)
        self.assertEqual(self.client.get(home).context["salas"], [self.laboratorio])
        self.assertRedirects(
            self.client.post(reverse("configuracoes"), {
                "acao": "preferencias_agenda",
                "todos_tipos": "on",
                "tipos_sala_preferidos": ["Laboratório"],
            }),
            reverse("configuracoes") + "#preferencias-agenda",
        )
        self.assertEqual(self.client.get(home).context["tipos_selecionados"], [])
        self.assertContains(
            self.client.get(reverse("configuracoes")), 'id="id_todos_tipos" checked',
        )

    def test_preferencia_ignora_tipos_inativos_e_rejeita_novas_opcoes_invalidas(self):
        self.usuario.tipos_sala_preferidos = ["Laboratório"]
        self.usuario.save(update_fields=["tipos_sala_preferidos"])
        self.laboratorio.ativa = False
        self.laboratorio.save(update_fields=["ativa"])

        resposta = self.client.get(reverse("home"))
        self.assertEqual(resposta.context["tipos_selecionados"], [])
        self.assertEqual(resposta.context["salas"], [self.sala_aula])
        resposta = self.client.post(reverse("configuracoes"), {
            "acao": "preferencias_agenda", "tipos_sala_preferidos": ["Laboratório"],
        })
        self.assertContains(resposta, "Um dos tipos selecionados está indisponível.")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.tipos_sala_preferidos, ["Laboratório"])

    def test_filtro_mantem_sala_restrita_na_agenda_e_fora_do_formulario_do_aluno(self):
        url = reverse("home")
        filtros = {"tipo": "Sala de aula", "data": "2026-11-16"}
        aluno = self.client.get(url, filtros)
        self.assertEqual(aluno.context["salas"], [self.sala_aula])
        self.assertEqual(aluno.context["salas_reservaveis"], [])
        self.assertContains(aluno, "Só professores")
        self.assertNotContains(aluno, f'<option value="{self.sala_aula.pk}">')

        self.usuario.perfil = "professor"
        self.usuario.save(update_fields=["perfil"])
        professor = self.client.get(url, filtros)
        self.assertEqual(professor.context["data_agenda"].isoformat(), "2026-11-16")
        self.assertEqual(professor.context["salas_reservaveis"], [self.sala_aula])
        self.assertContains(professor, f'<option value="{self.sala_aula.pk}">')
        self.assertNotContains(professor, "Só professores")

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

    def test_agenda_lembra_data_ao_voltar_e_apos_novo_login(self):
        home = reverse("home")
        data_escolhida = timezone.localdate() + timedelta(days=2)
        resposta = self.client.get(home, {"data": data_escolhida.isoformat()})
        self.assertEqual(resposta.context["data_agenda"], data_escolhida)

        self.client.get(reverse("minhas_reservas"))
        self.assertEqual(self.client.get(home).context["data_agenda"], data_escolhida)

        self.client.post(reverse("logout"))
        novo_cliente = Client()
        nome_cookie = f"salafacil_agenda_data_{self.usuario.pk}"
        novo_cliente.cookies[nome_cookie] = self.client.cookies[nome_cookie].value
        novo_cliente.force_login(self.usuario)
        self.assertEqual(novo_cliente.get(home).context["data_agenda"], data_escolhida)
        self.assertGreater(int(resposta.cookies[nome_cookie]["max-age"]), 0)

    def test_preferencia_de_data_nao_passa_para_outra_conta(self):
        home = reverse("home")
        data_escolhida = timezone.localdate() + timedelta(days=2)
        self.client.get(home, {"data": data_escolhida.isoformat()})
        self.client.post(reverse("logout"))

        outro_usuario = get_user_model().objects.create_user(
            email="outra-agenda@unifip.edu.br", password="SenhaSegura123!"
        )
        self.client.force_login(outro_usuario)
        self.assertEqual(self.client.get(home).context["data_agenda"], timezone.localdate())


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
            first_name="Ana",
            last_name="Silva",
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
        self.assertNotContains(resposta, 'title="Aula de programação"')

    def test_agenda_exibe_nome_do_responsavel_sem_revelar_email(self):
        self.criar_reserva(usuario=self.outro_usuario)

        resposta = self.client.get(reverse("home"), {
            "data": self.data_reserva.isoformat(), "tipo": "Laboratório",
        })

        self.assertContains(resposta, 'data-responsavel="Ana Silva"')
        self.assertNotContains(resposta, self.outro_usuario.email)

    def test_reserva_propria_exibe_finalidade_ao_passar_o_mouse(self):
        reserva = self.criar_reserva()

        resposta = self.client.get(
            reverse("home"),
            {"data": self.data_reserva.isoformat()},
        )

        self.assertContains(resposta, f'title="{reserva.finalidade}"')

    def test_reserva_cancelada_nao_ocupa_horario(self):
        self.criar_reserva(status=Reserva.Status.CANCELADA)

        intervalo = self.obter_intervalo()

        self.assertFalse(intervalo["ocupado"])
        self.assertIsNone(intervalo["reserva"])

    def test_reservas_seguidas_tem_cores_distintas_por_bloco(self):
        self.criar_reserva()
        Reserva.objects.create(
            sala=self.sala,
            usuario=self.outro_usuario,
            data=self.data_reserva,
            inicio=time(10, 0),
            fim=time(11, 0),
            finalidade="Reunião",
        )

        resposta = self.client.get(reverse("home"), {"data": self.data_reserva.isoformat()})
        cores = re.findall(r"--matiz-reserva: ([0-9.]+);", resposta.content.decode())

        self.assertEqual(len(cores), 4)
        self.assertEqual(cores[0], cores[1])
        self.assertEqual(cores[2], cores[3])
        self.assertNotEqual(cores[1], cores[2])

    def test_link_da_agenda_abre_apenas_as_reservas_do_usuario(self):
        propria = self.criar_reserva()
        outra = self.criar_reserva(usuario=self.outro_usuario)
        url = reverse("minhas_reservas")

        agenda = self.client.get(reverse("home"))
        self.assertContains(agenda, f'href="{url}"')
        self.assertNotContains(agenda, 'class="minhas-reservas-tabela"')

        resposta = self.client.get(url)
        self.assertContains(resposta, f'data-reserva-id="{propria.pk}"')
        self.assertNotContains(resposta, f'data-reserva-id="{outra.pk}"')
        self.assertNotContains(resposta, 'id="reserva-form"')

    def test_pagina_de_minhas_reservas_exige_login(self):
        self.client.logout()
        url = reverse("minhas_reservas")

        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_minhas_reservas_pagina_15_itens_do_titular(self):
        reservas = Reserva.objects.bulk_create([
            Reserva(
                usuario=self.usuario,
                sala=self.sala,
                data=self.data_reserva + timedelta(days=dia),
                inicio=time(9),
                fim=time(10),
                finalidade="Estudo",
            )
            for dia in range(16)
        ])
        self.criar_reserva(usuario=self.outro_usuario)
        url = reverse("minhas_reservas")

        primeira = self.client.get(url)
        self.assertContains(primeira, "Página 1 de 2")
        self.assertContains(primeira, 'href="?pagina=2"')
        self.assertEqual(list(primeira.context["minhas_reservas"]), reservas[:0:-1])

        segunda = self.client.get(url, {"pagina": 2})
        self.assertContains(segunda, "Página 2 de 2")
        self.assertContains(segunda, 'href="?pagina=1"')
        self.assertEqual(list(segunda.context["minhas_reservas"]), reservas[:1])
        self.assertContains(segunda, f'data-reserva-id="{reservas[0].pk}"')


class NotificacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.usuario = User.objects.create_user(
            email="notificacoes@unifip.edu.br", password="SenhaSegura123!"
        )
        cls.outro_usuario = User.objects.create_user(
            email="outras-notificacoes@unifip.edu.br", password="SenhaSegura123!"
        )
        cls.reserva = cls.agendar(cls.usuario, "Sala do titular")
        cls.outra_reserva = cls.agendar(cls.outro_usuario, "Sala de outra conta")

    @staticmethod
    def agendar(usuario, nome):
        sala = Sala.objects.create(
            nome=nome, nome_curto=nome, tipo="Sala de aula", localizacao="Bloco A",
            capacidade=30, permite_reserva_aluno=True,
        )
        return criar_reserva(
            usuario=usuario,
            sala_id=sala.pk,
            data=timezone.localdate() + timedelta(days=1),
            inicio=time(9),
            fim=time(10),
            finalidade="Aula",
        )

    def test_lista_eventos_do_titular_do_mais_recente_ao_mais_antigo(self):
        cancelar_reserva(usuario=self.usuario, reserva_id=self.reserva.pk)
        self.client.force_login(self.usuario)

        resposta = self.client.get(reverse("notificacoes"))
        self.assertContains(resposta, "Reserva cancelada")
        self.assertContains(resposta, "Reserva confirmada")
        self.assertContains(resposta, "Sala do titular")
        self.assertNotContains(resposta, "Sala de outra conta")
        self.assertContains(resposta, 'aria-label="Notificações: 2 não lidas"', count=2)
        self.assertEqual(self.client.get(reverse("home")).context["notificacoes_nao_lidas"], 2)
        self.assertEqual(self.client.get(reverse("minhas_reservas")).context["notificacoes_nao_lidas"], 2)
        self.assertEqual(
            [item.tipo for item in resposta.context["notificacoes"]],
            [Reserva.Status.CANCELADA, Reserva.Status.CONFIRMADA],
        )

    def test_preferencia_silencia_avisos_e_preserva_os_eventos_do_titular(self):
        self.client.force_login(self.usuario)
        lista = reverse("notificacoes")
        preferencia = reverse("preferencia_notificacoes")
        headers = {"Accept": "application/json"}
        configuracoes = reverse("configuracoes")
        self.assertContains(self.client.get(configuracoes), 'aria-checked="true"')
        resposta = self.client.post(
            preferencia, {"receber": "0", "usuario": self.outro_usuario.pk},
            headers=headers,
        )
        self.assertIs(resposta.json()["avisos_notificacoes_ativos"], False)

        self.client.logout()
        self.client.force_login(self.usuario)
        resposta = self.client.get(lista)
        self.assertContains(self.client.get(configuracoes), 'aria-checked="false"')
        self.assertContains(resposta, 'aria-label="Notificações"', count=2)
        self.assertContains(resposta, 'data-contador-notificacoes aria-hidden="true" hidden', count=2)
        resposta = self.client.post(reverse("bookings:criar_reserva"), {
            "sala_id": self.reserva.sala_id,
            "data": self.reserva.data.isoformat(),
            "inicio": "10:00",
            "fim": "11:00",
            "finalidade": "Estudo",
        }, content_type="application/json")
        self.assertEqual(resposta.status_code, 201)
        self.assertIs(resposta.json()["avisos_notificacoes_ativos"], False)
        reserva_sem_aviso = Reserva.objects.get(pk=resposta.json()["reserva_id"])

        resposta = self.client.post(
            reverse("bookings:cancelar_reserva", args=[self.reserva.pk]),
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIs(resposta.json()["avisos_notificacoes_ativos"], False)
        self.assertEqual(resposta.json()["notificacoes_nao_lidas"], 3)
        self.assertEqual(reserva_sem_aviso.notificacoes.get().tipo, Reserva.Status.CONFIRMADA)
        resposta = self.client.get(lista)
        self.assertContains(resposta, "Reserva confirmada", count=2)
        self.assertContains(resposta, "Reserva cancelada", count=1)
        self.assertContains(resposta, "Marcar todas como lidas")

        self.outro_usuario.refresh_from_db()
        self.assertTrue(self.outro_usuario.recebe_notificacoes_reserva)
        cancelar_reserva(
            usuario=self.outro_usuario, reserva_id=self.outra_reserva.pk,
        )
        self.assertEqual(self.outra_reserva.notificacoes.count(), 2)

        self.assertRedirects(self.client.post(preferencia, {"receber": "1"}), configuracoes)
        self.assertContains(self.client.get(lista), 'aria-label="Notificações: 3 não lidas"', count=2)

    def test_controle_de_avisos_aparece_apenas_em_configuracoes(self):
        configuracoes = reverse("configuracoes")
        notificacoes = reverse("notificacoes")
        preferencia = reverse("preferencia_notificacoes")
        client = self.client
        self.assertRedirects(
            client.get(configuracoes), f"{reverse('login')}?next={configuracoes}",
        )
        client.force_login(self.usuario)
        self.assertContains(client.get(reverse("home")), f'href="{configuracoes}"')
        resposta = client.get(configuracoes)
        self.assertContains(resposta, "Configurações")
        self.assertContains(resposta, f'action="{preferencia}"')
        self.assertContains(resposta, 'role="switch"')
        self.assertIn("no-store", resposta.headers["Cache-Control"])

        resposta = client.get(notificacoes)
        self.assertNotContains(resposta, f'action="{preferencia}"')
        self.assertNotContains(resposta, 'role="switch"')

    def test_preferencia_exige_login_post_csrf_e_valor_valido(self):
        url = reverse("preferencia_notificacoes")
        client = Client(enforce_csrf_checks=True)
        self.assertRedirects(client.get(url), f"{reverse('login')}?next={url}")
        client.force_login(self.usuario)
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url, {"receber": "0"}).status_code, 403)
        client.get(reverse("notificacoes"))
        resposta = client.post(
            url, {"receber": "invalido"},
            headers={"X-CSRFToken": client.cookies["csrftoken"].value},
        )
        self.assertEqual(resposta.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.recebe_notificacoes_reserva)

    def test_exige_login_para_consultar_e_marcar_como_lida(self):
        lista = reverse("notificacoes")
        leitura = reverse("ler_notificacao", args=[self.reserva.notificacoes.get().pk])
        leitura_total = reverse("ler_todas_notificacoes")
        self.assertRedirects(self.client.get(lista), f"{reverse('login')}?next={lista}")
        self.assertRedirects(self.client.post(leitura), f"{reverse('login')}?next={leitura}")
        self.assertRedirects(
            self.client.post(leitura_total), f"{reverse('login')}?next={leitura_total}"
        )

    def test_sincronizacao_mostra_apenas_estado_e_eventos_do_titular(self):
        estado_url = reverse("estado_notificacoes")
        self.assertRedirects(self.client.get(estado_url), f"{reverse('login')}?next={estado_url}")
        self.client.force_login(self.usuario)
        cancelar_reserva(usuario=self.usuario, reserva_id=self.reserva.pk)
        ultima = self.reserva.notificacoes.get(tipo=Reserva.Status.CANCELADA)

        resposta = self.client.get(estado_url)
        self.assertEqual(resposta.json(), {
            "notificacoes_nao_lidas": 2, "ultima_notificacao_id": ultima.pk,
            "avisos_notificacoes_ativos": True,
        })
        self.assertIn("no-store", resposta.headers["Cache-Control"])
        fragmento = self.client.get(reverse("notificacoes"), {"fragmento": "lista"})
        self.assertContains(fragmento, "Reserva cancelada")
        self.assertNotContains(fragmento, "Sala de outra conta")
        self.assertNotContains(fragmento, "<!DOCTYPE html>")

    def test_leitura_exige_post_com_csrf_e_so_altera_notificacao_propria(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        propria = self.reserva.notificacoes.get()
        outra = self.outra_reserva.notificacoes.get()
        url = reverse("ler_notificacao", args=[propria.pk])
        url_outra = reverse("ler_notificacao", args=[outra.pk])

        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        client.get(reverse("notificacoes"))
        headers = {
            "Accept": "application/json",
            "X-CSRFToken": client.cookies["csrftoken"].value,
        }
        self.assertEqual(client.post(url_outra, headers=headers).status_code, 404)
        esperado = {
            "lida": True, "tem_nao_lidas": False, "notificacoes_nao_lidas": 0,
            "ultima_notificacao_id": propria.pk, "avisos_notificacoes_ativos": True,
        }
        self.assertEqual(client.post(url, headers=headers).json(), esperado)
        self.assertEqual(client.post(url, headers=headers).json(), esperado)
        propria.refresh_from_db()
        outra.refresh_from_db()
        self.assertTrue(propria.lida)
        self.assertFalse(outra.lida)

    def test_leitura_em_lote_alcanca_outras_paginas_e_preserva_outra_conta(self):
        reservas = Reserva.objects.bulk_create([
            Reserva(
                usuario=self.usuario,
                sala=self.reserva.sala,
                data=self.reserva.data + timedelta(days=dia),
                inicio=time(9),
                fim=time(10),
                finalidade="Estudo",
            )
            for dia in range(1, 11)
        ])
        NotificacaoReserva.objects.bulk_create([
            NotificacaoReserva(reserva=reserva, tipo=Reserva.Status.CONFIRMADA)
            for reserva in reservas
        ])

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        lista = reverse("notificacoes")
        url = reverse("ler_todas_notificacoes")
        propria = self.reserva.notificacoes.get()
        outra = self.outra_reserva.notificacoes.get()

        self.assertEqual(client.post(url).status_code, 403)
        primeira_pagina = client.get(lista)
        self.assertContains(primeira_pagina, "Página 1 de 2")
        self.assertContains(primeira_pagina, 'href="?pagina=2"')
        self.assertEqual(len(primeira_pagina.context["notificacoes"]), 10)
        self.assertEqual(primeira_pagina.context["notificacoes_nao_lidas"], 11)
        self.assertNotIn(propria, primeira_pagina.context["notificacoes"])
        self.assertEqual(client.get(url).status_code, 405)

        headers = {
            "Accept": "application/json",
            "X-CSRFToken": client.cookies["csrftoken"].value,
        }
        esperado = {
            "lida": True, "tem_nao_lidas": False, "notificacoes_nao_lidas": 0,
            "ultima_notificacao_id": primeira_pagina.context["ultima_notificacao_id"],
            "avisos_notificacoes_ativos": True,
        }
        self.assertEqual(client.post(url, headers=headers).json(), esperado)
        self.assertEqual(client.post(url, headers=headers).json(), esperado)
        segunda_pagina = client.get(lista, {"pagina": 2})
        self.assertContains(segunda_pagina, "Página 2 de 2")
        self.assertEqual(list(segunda_pagina.context["notificacoes"]), [propria])
        self.assertEqual(segunda_pagina.context["notificacoes_nao_lidas"], 0)
        propria.refresh_from_db()
        outra.refresh_from_db()
        self.assertTrue(propria.lida)
        self.assertFalse(outra.lida)
