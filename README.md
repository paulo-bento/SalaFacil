# SalaFácil!

O SalaFácil! é um sistema para consultar a disponibilidade e reservar salas e auditórios do seu campus.

- **Agenda e reservas** — consulta de horários ocupados, filtros e bloqueio de reservas sobrepostas.
- **Perfis acadêmicos** — alunos reservam ambientes liberados para seu perfil. Professores podem reservar salas ativas.
- **Notificações e preferências** — histórico de confirmações e cancelamentos, controle de avisos e seleção dos tipos de sala exibidos por padrão.

O projeto usa Python, Django, PostgreSQL, Django Templates, CSS e JavaScript.

## Como rodar localmente

Você precisa de **Git**, **Python 3.14** (versão usada na validação) e **PostgreSQL** instalado e em execução.

### 1. Clone o projeto e instale as dependências

```bash
git clone https://github.com/paulo-bento/SalaFacil.git
cd SalaFacil
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Se o ambiente já existir, basta ativá-lo com `source .venv/bin/activate`.

### 2. Prepare o PostgreSQL

O Django usa o banco `salafacil`, com o usuário `salafacil_user`, em `127.0.0.1:5432`. Se o usuário e o banco ainda não existirem, execute no `psql` com uma conta administrativa do PostgreSQL:

```sql
CREATE ROLE salafacil_user LOGIN;
\password salafacil_user
CREATE DATABASE salafacil OWNER salafacil_user;
```

### 3. Configure o arquivo `.env`

Crie o arquivo `.env` na mesma pasta de `manage.py`. Gere uma chave local para o Django:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Preencha as quatro variáveis:

```dotenv
SECRET_KEY=cole_a_chave_gerada
SALAFACIL_DB_PASSWORD=senha_definida_no_postgresql
EMAIL_HOST_USER=seu_email@gmail.com
EMAIL_HOST_PASSWORD=credencial_smtp
```

Use a mesma senha definida no PostgreSQL. Os campos de e-mail podem ter valores fictícios para testar a agenda localmente. Para enviar mensagens de recuperação de senha, preencha-os com uma conta Gmail e uma credencial SMTP válida. Guarde o `.env` localmente.

### 4. Aplique as migrações e inicie o servidor

```bash
python manage.py check
python manage.py migrate --plan
python manage.py migrate
python manage.py runserver
```

Abra [http://127.0.0.1:8000/](http://127.0.0.1:8000/). O cadastro público cria contas com perfil **Aluno**.

Em um banco novo, cadastre pelo menos uma sala para testar as reservas. Em outro terminal, com o ambiente virtual ativado, crie um administrador:

```bash
python manage.py createsuperuser
```

Entre na [administração](http://127.0.0.1:8000/admin/), abra **Salas** e cadastre um ambiente ativo. Para testar com uma conta de aluno, marque **Permite reserva por alunos** na sala.

Para instruções de Windows, diagnóstico do ambiente e execução dos testes, consulte o [guia de desenvolvimento](docs/guia-desenvolvimento.md).
