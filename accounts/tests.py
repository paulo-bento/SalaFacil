from django.test import Client, TestCase

from .forms import RegistrationForm
from .models import User
from rooms.models import Sala


from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


class MinhaContaTests(TestCase):
    senha_atual = "SenhaInicial123!"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.usuario = User.objects.create_user(
            email="minha-conta@unifip.edu.br", password=cls.senha_atual,
            first_name="Maria", last_name="Silva", perfil=User.Perfil.PROFESSOR,
        )

    def setUp(self) -> None:
        self.url = reverse("configuracoes")
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.usuario)
        self.client.get(self.url)

    def enviar(self, acao: str, **dados: str):
        return self.client.post(self.url, {
            **dados, "acao": acao,
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })

    def test_edita_apenas_os_nomes_da_conta_autenticada(self) -> None:
        resposta = self.enviar(
            "dados_pessoais", first_name="  Ana Maria  ", last_name="Souza",
            email="outro@unifip.edu.br", perfil=User.Perfil.ALUNO,
        )
        self.assertRedirects(resposta, self.url + "#dados-pessoais", fetch_redirect_response=False)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Ana Maria")
        self.assertEqual(self.usuario.last_name, "Souza")
        self.assertEqual(self.usuario.email, "minha-conta@unifip.edu.br")
        self.assertEqual(self.usuario.perfil, User.Perfil.PROFESSOR)
        pagina = self.client.get(self.url)
        self.assertContains(pagina, "Ana Maria")
        self.assertContains(
            pagina, 'data-aviso-inicial="success">Dados pessoais atualizados.',
        )

    def test_nome_invalido_ou_sem_csrf_nao_altera_dados(self) -> None:
        resposta = self.client.post(self.url, {
            "acao": "dados_pessoais", "first_name": "Ana", "last_name": "Souza",
        })
        self.assertEqual(resposta.status_code, 403)
        resposta = self.enviar("dados_pessoais", first_name="Ana", last_name="")
        self.assertIn("last_name", resposta.context["dados_pessoais"].errors)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Maria")
        self.assertEqual(self.usuario.last_name, "Silva")

    def test_configuracoes_rejeita_troca_de_senha(self) -> None:
        self.assertNotContains(self.client.get(self.url), 'name="old_password"')
        resposta = self.enviar("alterar_senha", old_password=self.senha_atual)
        self.assertEqual(resposta.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.senha_atual))


class RegistrationFormTests(TestCase):
    def setUp(self):
        self.dados = {
            "first_name": "Maria",
            "last_name": "Silva",
            "email": "maria@unifip.edu.br",
            "password1": "SenhaSegura123!",
            "password2": "SenhaSegura123!",
        }

    def test_cadastro_valido(self):
        formulario = RegistrationForm(data=self.dados)

        self.assertTrue(formulario.is_valid(), formulario.errors)

        usuario = formulario.save()

        self.assertEqual(usuario.first_name, "Maria")
        self.assertEqual(usuario.last_name, "Silva")
        self.assertEqual(usuario.email, "maria@unifip.edu.br")
        self.assertTrue(usuario.check_password("SenhaSegura123!"))

    def test_nome_obrigatorio(self):
        self.dados["first_name"] = ""

        formulario = RegistrationForm(data=self.dados)

        self.assertFalse(formulario.is_valid())
        self.assertIn("first_name", formulario.errors)

    def test_sobrenome_obrigatorio(self):
        self.dados["last_name"] = ""

        formulario = RegistrationForm(data=self.dados)

        self.assertFalse(formulario.is_valid())
        self.assertIn("last_name", formulario.errors)

    def test_email_duplicado(self):
        User.objects.create_user(
            email="maria@unifip.edu.br",
            password="SenhaSegura123!",
        )

        self.dados["email"] = "MARIA@unifip.edu.br"

        formulario = RegistrationForm(data=self.dados)

        self.assertFalse(formulario.is_valid())
        self.assertIn("email", formulario.errors)

    def test_dominio_email_invalido(self):
        self.dados["email"] = "maria@outlook.com"

        formulario = RegistrationForm(data=self.dados)

        self.assertFalse(formulario.is_valid())
        self.assertIn("email", formulario.errors)

    def test_email_gmail_permitido(self):
        self.dados["email"] = "maria@gmail.com"

        formulario = RegistrationForm(data=self.dados)

        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_senhas_diferentes(self):
        self.dados["password2"] = "OutraSenha123!"

        formulario = RegistrationForm(data=self.dados)

        self.assertFalse(formulario.is_valid())
        self.assertIn("password2", formulario.errors)


class RegistrationViewTests(TestCase):
    def test_cadastro_cria_usuario_e_redireciona(self):
        resposta = self.client.post(
            "/accounts/register/",
            {
                "first_name": "Maria",
                "last_name": "Silva",
                "email": "maria@unifip.edu.br",
                "password1": "SenhaSegura123!",
                "password2": "SenhaSegura123!",
                "perfil": User.Perfil.PROFESSOR,
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.url, "/accounts/login/")

        usuario = User.objects.get(email="maria@unifip.edu.br")

        self.assertEqual(usuario.first_name, "Maria")
        self.assertEqual(usuario.last_name, "Silva")
        self.assertEqual(usuario.perfil, User.Perfil.ALUNO)
        self.assertTrue(usuario.check_password("SenhaSegura123!"))


class PerfilAcademicoTests(TestCase):
    senha = "SenhaSegura123!"

    @classmethod
    def setUpTestData(cls):
        cls.aluno = User.objects.create_user(email="aluno@unifip.edu.br", password=cls.senha)
        cls.professor = User.objects.create_user(
            email="professor@unifip.edu.br", password=cls.senha, perfil=User.Perfil.PROFESSOR,
        )
        cls.administrador = User.objects.create_superuser(
            email="admin.perfil@unifip.edu.br", password=cls.senha,
        )

    def test_login_por_email_e_senha_exige_perfil_correspondente(self):
        for usuario in (self.aluno, self.professor):
            with self.subTest(perfil=usuario.perfil):
                resposta = self.client.post(reverse("login"), {
                    "email": usuario.email, "password": self.senha, "perfil": usuario.perfil,
                })
                self.assertRedirects(resposta, reverse("home"))
                self.assertEqual(self.client.session["_auth_user_id"], str(usuario.pk))
                self.client.logout()

    def test_perfil_incorreto_ou_ausente_falha_com_mensagem_generica(self):
        for email, perfil in ((self.aluno.email, "professor"), ("ausente@unifip.edu.br", "professor"),
                              (self.aluno.email, ""), (self.aluno.email, "admin")):
            with self.subTest(email=email, perfil=perfil):
                resposta = self.client.post(reverse("login"), {
                    "email": email, "password": self.senha, "perfil": perfil,
                })
                self.assertContains(resposta, "E-mail, senha ou perfil inválidos.")
                self.assertNotIn("_auth_user_id", self.client.session)
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.perfil, User.Perfil.ALUNO)

    def test_login_admin_independe_da_escolha_de_perfil(self):
        resposta = self.client.post(reverse("admin:login"), {
            "username": self.administrador.email, "password": self.senha, "next": reverse("admin:index"),
        })
        self.assertRedirects(resposta, reverse("admin:index"))

    def test_somente_admin_autorizado_pode_alterar_perfil(self):
        url = reverse("admin:accounts_user_change", args=[self.aluno.pk])
        dados = {
            "email": self.aluno.email, "perfil": User.Perfil.PROFESSOR, "is_active": "on",
            "date_joined_0": "2026-11-15", "date_joined_1": "10:00:00",
        }
        self.client.force_login(self.aluno)
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.perfil, User.Perfil.ALUNO)

        self.client.force_login(self.administrador)
        self.assertRedirects(self.client.post(url, dados), reverse("admin:accounts_user_changelist"))
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.perfil, User.Perfil.PROFESSOR)
        self.assertFalse(self.aluno.is_staff)

    def test_admin_pode_autorizar_sala_para_alunos(self):
        campos = {"nome": "Sala de Estudos", "nome_curto": "Estudos", "tipo": "Estudo",
                  "localizacao": "Bloco A", "capacidade": 20}
        sala = Sala.objects.create(**campos)
        self.assertFalse(sala.permite_reserva_aluno)
        self.client.force_login(self.administrador)

        resposta = self.client.post(reverse("admin:rooms_sala_change", args=[sala.pk]), {
            **campos, "ativa": "on", "permite_reserva_aluno": "on",
        })

        self.assertRedirects(resposta, reverse("admin:rooms_sala_changelist"))
        sala.refresh_from_db()
        self.assertTrue(sala.permite_reserva_aluno)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class RecuperacaoSenhaTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            email="recuperacao@unifip.edu.br",
            password="SenhaAntiga123!",
            is_active=True,
        )

    def test_pagina_de_recuperacao_carrega(self):
        resposta = self.client.get(reverse("password_reset"))

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(
            resposta,
            "accounts/password_reset.html",
        )

    def test_solicitacao_envia_email(self):
        resposta = self.client.post(
            reverse("password_reset"),
            {"email": self.usuario.email},
        )

        self.assertRedirects(
            resposta,
            reverse("password_reset_done"),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [self.usuario.email],
        )
        self.assertIn(
            "/accounts/reset/",
            mail.outbox[0].body,
        )

    def test_email_nao_cadastrado_nao_revela_conta(self):
        resposta = self.client.post(
            reverse("password_reset"),
            {"email": "inexistente@unifip.edu.br"},
        )

        self.assertRedirects(
            resposta,
            reverse("password_reset_done"),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_link_valido_permita_redefinir_senha(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        token = default_token_generator.make_token(self.usuario)

        url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )

        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 302)

        resposta = self.client.post(
            resposta.url,
            {
                "new_password1": "SenhaNova123!",
                "new_password2": "SenhaNova123!",
            },
        )

        self.assertRedirects(
            resposta,
            reverse("password_reset_complete"),
        )

        self.usuario.refresh_from_db()
        self.assertTrue(
            self.usuario.check_password("SenhaNova123!")
        )
        self.assertFalse(
            self.usuario.check_password("SenhaAntiga123!")
        )

    def test_token_invalido_eh_rejeitado(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))

        resposta = self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={
                    "uidb64": uid,
                    "token": "token-invalido",
                },
            )
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(
            resposta,
            "Link inválido ou expirado",
        )

    def test_link_nao_pode_ser_reutilizado(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        token = default_token_generator.make_token(self.usuario)

        url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )

        resposta = self.client.get(url)

        self.client.post(
            resposta.url,
            {
                "new_password1": "SenhaNova123!",
                "new_password2": "SenhaNova123!",
            },
        )

        nova_resposta = self.client.get(url)

        self.assertContains(
            nova_resposta,
            "Link inválido ou expirado",
        )
