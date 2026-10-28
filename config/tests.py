"""
Testes da configuração do projeto SalaFácil (pacote ``config``).

Cobrem settings.py, urls.py, wsgi.py e asgi.py. Nenhum teste acessa o banco
de dados (todos usam SimpleTestCase), então rodam mesmo sem o PostgreSQL ativo:

    python manage.py test config
"""

import importlib
import os
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import URLResolver, resolve, reverse


class VariaveisDeAmbienteTests(SimpleTestCase):
    """SECRET_KEY e senha do banco devem vir do ambiente / .env."""

    def test_secret_key_vem_do_ambiente(self):
        self.assertTrue(settings.SECRET_KEY)
        self.assertEqual(settings.SECRET_KEY, os.environ["SECRET_KEY"])

    def test_senha_do_banco_vem_do_ambiente(self):
        self.assertEqual(
            settings.DATABASES["default"]["PASSWORD"],
            os.environ["SALAFACIL_DB_PASSWORD"],
        )

    def _importar_settings_sem(self, variavel):
        """Reimporta config.settings sem a variável e sem ler o .env."""
        env = {k: v for k, v in os.environ.items() if k != variavel}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch("dotenv.load_dotenv", return_value=False):
            sys.modules.pop("config.settings", None)
            try:
                importlib.import_module("config.settings")
            finally:
                sys.modules.pop("config.settings", None)

    def test_falha_se_secret_key_ausente(self):
        with self.assertRaises(KeyError):
            self._importar_settings_sem("SECRET_KEY")

    def test_falha_se_senha_do_banco_ausente(self):
        with self.assertRaises(KeyError):
            self._importar_settings_sem("SALAFACIL_DB_PASSWORD")



class BancoDeDadosTests(SimpleTestCase):
    def test_configuracao_postgres(self):
        db = settings.DATABASES["default"]

        self.assertEqual(
            db["ENGINE"],
            "django.db.backends.postgresql",
        )

        self.assertEqual(
            db["NAME"],
            "test_salafacil",
        )

        self.assertEqual(db["USER"], "salafacil_user")
        self.assertEqual(db["HOST"], "127.0.0.1")
        self.assertEqual(db["PORT"], "5432")



class AppsEUsuarioTests(SimpleTestCase):
    def test_apps_do_projeto_instalados(self):
        for app in ("accounts", "core", "rooms", "bookings"):
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_apps_contrib_essenciais_instalados(self):
        for app in (
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ):
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_sem_apps_duplicados(self):
        self.assertEqual(len(settings.INSTALLED_APPS), len(set(settings.INSTALLED_APPS)))

    def test_modelo_de_usuario_customizado(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        User = get_user_model()
        self.assertEqual(User._meta.app_label, "accounts")
        self.assertEqual(User.__name__, "User")


class MiddlewareTests(SimpleTestCase):
    def test_middlewares_essenciais_presentes(self):
        for mw in (
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ):
            self.assertIn(mw, settings.MIDDLEWARE)

    def test_ordem_dos_middlewares(self):
        mw = settings.MIDDLEWARE
        self.assertEqual(mw[0], "django.middleware.security.SecurityMiddleware")
        # Sessão precisa vir antes de autenticação e de mensagens.
        sess = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
        self.assertLess(sess, mw.index("django.contrib.auth.middleware.AuthenticationMiddleware"))
        self.assertLess(sess, mw.index("django.contrib.messages.middleware.MessageMiddleware"))


class TemplatesEStaticTests(SimpleTestCase):
    def test_pasta_de_templates_do_projeto(self):
        tpl = settings.TEMPLATES[0]
        self.assertIn(settings.BASE_DIR / "templates", tpl["DIRS"])
        self.assertTrue(tpl["APP_DIRS"])
        self.assertIn(
            "django.template.context_processors.request",
            tpl["OPTIONS"]["context_processors"],
        )

    def test_static(self):
        self.assertEqual(settings.STATIC_URL, "/static/")  # Django adiciona a barra inicial
        self.assertIn(settings.BASE_DIR / "static", settings.STATICFILES_DIRS)

    def test_base_dir_eh_a_raiz_do_projeto(self):
        base = Path(settings.BASE_DIR)
        self.assertTrue((base / "config" / "settings.py").exists())
        self.assertTrue((base / "manage.py").exists())


class InternacionalizacaoTests(SimpleTestCase):
    def test_idioma_e_fuso(self):
        self.assertEqual(settings.LANGUAGE_CODE, "pt-br")
        self.assertEqual(settings.TIME_ZONE, "America/Fortaleza")
        self.assertTrue(settings.USE_I18N)
        self.assertTrue(settings.USE_TZ)


class UrlsTests(SimpleTestCase):
    def _prefixos(self):
        from config import urls
        return [str(p.pattern) for p in urls.urlpatterns]

    def test_prefixos_registrados(self):
        self.assertEqual(self._prefixos(), ["admin/", "accounts/", "bookings/", ""])

    def test_includes_apontam_para_os_apps_certos(self):
        from config import urls
        esperado = {"accounts/": "accounts.urls", "bookings/": "bookings.urls", "": "core.urls"}
        for p in urls.urlpatterns:
            prefixo = str(p.pattern)
            if prefixo in esperado:
                self.assertIsInstance(p, URLResolver)
                self.assertEqual(p.urlconf_module.__name__, esperado[prefixo])

    def test_rota_vazia_do_core_fica_por_ultimo(self):
        # O include("core.urls") com prefixo "" deve ser o último para não
        # "engolir" rotas declaradas depois dele.
        self.assertEqual(self._prefixos()[-1], "")

    def test_admin_resolve(self):
        self.assertEqual(reverse("admin:index"), "/admin/")
        self.assertEqual(resolve("/admin/").app_name, "admin")

    def test_admin_redireciona_anonimo_para_login(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    def test_pagina_de_login_do_admin_carrega(self):
        resp = self.client.get("/admin/login/")
        self.assertEqual(resp.status_code, 200)


class ServidoresTests(SimpleTestCase):
    def test_wsgi_application(self):
        from django.core.handlers.wsgi import WSGIHandler
        from config.wsgi import application
        self.assertIsInstance(application, WSGIHandler)
        self.assertEqual(settings.WSGI_APPLICATION, "config.wsgi.application")

    def test_asgi_application(self):
        from django.core.handlers.asgi import ASGIHandler
        from config.asgi import application
        self.assertIsInstance(application, ASGIHandler)

    def test_settings_module_padrao(self):
        self.assertEqual(os.environ.get("DJANGO_SETTINGS_MODULE"), "config.settings")


class SystemCheckTests(SimpleTestCase):
    def test_django_check_sem_erros(self):
        # Levanta SystemCheckError se houver qualquer erro de configuração.
        call_command("check", verbosity=0)
