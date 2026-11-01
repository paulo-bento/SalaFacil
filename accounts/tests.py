
from django.test import TestCase

from .forms import RegistrationForm
from .models import User


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
