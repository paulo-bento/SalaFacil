import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .permissions import somente_admin

User = get_user_model()

SENHA = "SenhaForte#2026x"
NOVA_SENHA = "OutraSenha#2026y"


class RotasNomeadasTests(TestCase):
    def test_named_routes_existem(self):
        for nome in ("login", "logout", "register", "password_reset",
                     "password_reset_done", "password_reset_complete"):
            self.assertTrue(reverse(nome))


class CadastroTests(TestCase):
    def test_cadastro_valido(self):
        resp = self.client.post(reverse("register"), {
            "email": "aluno@unifip.edu.br",
            "password1": SENHA,
            "password2": SENHA,
        })
        self.assertRedirects(resp, reverse("login"))
        user = User.objects.get(email="aluno@unifip.edu.br")
        self.assertFalse(user.is_staff)

    def test_cadastro_dominio_invalido(self):
        resp = self.client.post(reverse("register"), {
            "email": "aluno@outrodominio.com",
            "password1": SENHA,
            "password2": SENHA,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_register_senhas_diferentes(self):
        resp = self.client.post(reverse("register"), {
            "email": "aluno@unifip.edu.br",
            "password1": SENHA,
            "password2": "diferente",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertContains(resp, "aluno@unifip.edu.br")
        self.assertNotContains(resp, SENHA)

    def test_register_email_duplicado_nao_revela(self):
        User.objects.create_user("aluno@unifip.edu.br", SENHA)
        resp = self.client.post(reverse("register"), {
            "email": "Aluno@unifip.edu.br",
            "password1": NOVA_SENHA,
            "password2": NOVA_SENHA,
        })
        self.assertRedirects(resp, reverse("login"))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["aluno@unifip.edu.br"])

    def test_register_email_duplicado_senha_ruim(self):
        User.objects.create_user("aluno@unifip.edu.br", SENHA)
        resp = self.client.post(reverse("register"), {
            "email": "aluno@unifip.edu.br",
            "password1": NOVA_SENHA,
            "password2": "diferente",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "já está cadastrado")
        self.assertContains(resp, "aluno@unifip.edu.br")
        self.assertEqual(len(mail.outbox), 0)


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("aluno@unifip.edu.br", SENHA)

    def test_login_ok(self):
        resp = self.client.post(reverse("login"), {
            "email": "aluno@unifip.edu.br", "password": SENHA,
        })
        self.assertRedirects(resp, reverse("home"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_senha_errada_msg_generica(self):
        resp = self.client.post(reverse("login"), {
            "email": "aluno@unifip.edu.br", "password": "errada",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "E-mail ou senha inválidos.")
        self.assertContains(resp, "aluno@unifip.edu.br")
        self.assertNotContains(resp, "errada")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_email_inexistente(self):
        resp = self.client.post(reverse("login"), {
            "email": "naoexiste@unifip.edu.br", "password": SENHA,
        })
        self.assertContains(resp, "E-mail ou senha inválidos.")

    def test_logout_ok(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_via_get(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)


class AcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.comum = User.objects.create_user("aluno@unifip.edu.br", SENHA)
        cls.admin = User.objects.create_user(
            "admin@unifip.edu.br", SENHA, is_staff=True, is_superuser=True,
        )

    def test_home_precisa_de_login(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp["Location"])

    def test_home_logado(self):
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_criar_reserva_anonimo_401(self):
        resp = self.client.post(
            reverse("bookings:criar_reserva"), data="{}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_admin_site_bloqueia_comum(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_admin_site_staff_entra(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_decorator_somente_admin(self):
        from django.http import HttpResponse

        @somente_admin
        def view(request):
            return HttpResponse("ok")

        rf = RequestFactory()

        req = rf.get("/x/")
        req.user = type("Anon", (), {"is_authenticated": False})()
        self.assertEqual(view(req).status_code, 302)

        req.user = self.comum
        with self.assertRaises(PermissionDenied):
            view(req)

        req.user = self.admin
        self.assertEqual(view(req).status_code, 200)


class RecuperacaoSenhaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("aluno@unifip.edu.br", SENHA)

    def get_link(self):
        self.client.post(reverse("password_reset"), {"email": "aluno@unifip.edu.br"})
        self.assertEqual(len(mail.outbox), 1)
        return re.search(r"https?://testserver\S+", mail.outbox[0].body).group(0)

    def test_pedido_manda_email(self):
        link = self.get_link()
        self.assertIn("/senha/redefinir/", link)
        self.assertNotIn(SENHA, mail.outbox[0].body)

    def test_mesma_resposta_com_email_inexistente(self):
        r1 = self.client.post(reverse("password_reset"), {"email": "aluno@unifip.edu.br"})
        r2 = self.client.post(reverse("password_reset"), {"email": "ninguem@unifip.edu.br"})
        self.assertRedirects(r1, reverse("password_reset_done"))
        self.assertRedirects(r2, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)  # só o cadastrado recebeu

    def test_token_valido(self):
        link = self.get_link()
        resp = self.client.get(link, follow=True)
        self.assertEqual(resp.status_code, 200)
        url_form = resp.redirect_chain[-1][0]

        resp = self.client.post(url_form, {
            "new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA,
        })
        self.assertRedirects(resp, reverse("password_reset_complete"))

        self.assertTrue(self.client.login(email="aluno@unifip.edu.br", password=NOVA_SENHA))
        self.client.logout()
        self.assertFalse(self.client.login(email="aluno@unifip.edu.br", password=SENHA))

    def test_token_invalid(self):
        resp = self.client.get(reverse("password_reset_confirm", args=["abc", "token-falso"]))
        self.assertContains(resp, "inválido ou expirou")

    def test_token_reusado(self):
        link = self.get_link()
        resp = self.client.get(link, follow=True)
        self.client.post(resp.redirect_chain[-1][0], {
            "new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA,
        })
        resp = self.client.get(link)
        self.assertContains(resp, "inválido ou expirou")

    def test_token_expirado(self):
        link = self.get_link()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            resp = self.client.get(link)
        self.assertContains(resp, "inválido ou expirou")
