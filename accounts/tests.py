from django.test import TestCase

from .forms import RegistrationForm
from .models import User


from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

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
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.url, "/accounts/login/")

        usuario = User.objects.get(email="maria@unifip.edu.br")

        self.assertEqual(usuario.first_name, "Maria")
        self.assertEqual(usuario.last_name, "Silva")
        self.assertTrue(usuario.check_password("SenhaSegura123!"))


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
