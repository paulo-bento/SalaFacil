# Guia de ambiente e validação — SalaFácil

Execute os comandos a partir da raiz do repositório. As regras de trabalho estão no [AGENTS.md](../AGENTS.md) e a validação mais recente, no [estado atual](estado-atual.md).

## 2. Preparação local

### Python e dependências

Ambiente verificado em 14/11/2026: Python 3.14.10, Django 5.2.18 e PostgreSQL
cliente 18.6. Não há `pyproject.toml`, lock separado ou versão de Python declarada
pelo projeto. Use Python 3.14 para reproduzir o ambiente validado.

Dependências declaradas: asgiref 3.12.1, Django 5.2.18, psycopg 3.3.6,
psycopg-binary 3.3.6, python-dotenv 1.2.4 e sqlparse 0.6.0.

Na raiz, crie o ambiente somente se ainda não existir:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

No PowerShell, use `py -3.14 -m venv .venv` e
`.\.venv\Scripts\Activate.ps1`. Também é possível chamar diretamente
`.\.venv\Scripts\python.exe` sem ativação. No Linux, o equivalente é
`.venv/bin/python`. Não recrie um ambiente existente sem verificar seu estado.

### Variáveis de ambiente

`config/settings.py` usa `load_dotenv(BASE_DIR / ".env")`. Variáveis já exportadas
no processo têm precedência. Se `.env` não existir, crie o arquivo na raiz do
repositório, ao lado de `manage.py`. Adicione as quatro variáveis da tabela
abaixo, uma por linha, no formato `NOME=valor`, e preencha os valores localmente.
Preserve o `.env` se ele já estiver configurado.

As quatro variáveis são acessadas por `os.environ[...]` e precisam estar definidas:

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Chave secreta do Django |
| `SALAFACIL_DB_PASSWORD` | Senha do usuário PostgreSQL configurado |
| `EMAIL_HOST_USER` | Conta remetente SMTP |
| `EMAIL_HOST_PASSWORD` | Credencial SMTP da conta remetente |

Gere uma chave local com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
e guarde-a somente no `.env`. Não registre a saída em documentação ou commits.

`DEBUG=True` e `ALLOWED_HOSTS=[]` são valores fixos no código, não variáveis
carregadas do `.env`. Com DEBUG ativo, use localhost/127.0.0.1 no desenvolvimento.
Essas configurações não constituem uma configuração de produção.

O e-mail utiliza Gmail SMTP, porta 587 e TLS. Para envio real, configure a conta
e sua credencial apropriada. Os testes de recuperação usam backend em memória;
valores fictícios definidos nas variáveis de e-mail bastam para a suíte, sem
conectar ao Gmail. Isso não valida envio real de mensagens.

### PostgreSQL

O destino está fixado em `config/settings.py`:

| Campo | Valor |
| --- | --- |
| Engine | `django.db.backends.postgresql` |
| Banco | `salafacil` |
| Usuário | `salafacil_user` |
| Host/porta | `127.0.0.1:5432` |
| Senha | `SALAFACIL_DB_PASSWORD` |

Não existem variáveis `DATABASE_URL`, `DB_NAME` ou `DB_HOST` implementadas.
Não substitua PostgreSQL por SQLite para contornar problemas de ambiente.

Verifique a instalação e a conexão:

```bash
psql --version
pg_isready -h 127.0.0.1 -p 5432
psql -h 127.0.0.1 -p 5432 -U salafacil_user -d salafacil -W -c "SELECT current_database(), current_user;"
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Conexão Django OK')"
```

No Arch, a instalação usa `sudo pacman -S postgresql`; para um cluster já
inicializado, o serviço pode ser iniciado com `sudo systemctl start postgresql`.
Não execute `initdb` sobre dados existentes. Uma instalação nova precisa de
cluster inicializado pelo administrador antes de iniciar o serviço.

Se banco/usuário estiverem ausentes, um administrador pode executar os comandos
abaixo em `psql`, **somente após confirmar que esses objetos não existem**:

```sql
CREATE ROLE salafacil_user LOGIN CREATEDB;
\password salafacil_user
CREATE DATABASE salafacil OWNER salafacil_user;
```

Use a mesma senha no `.env`. Para um usuário existente sem permissão de testes,
o administrador deve avaliar `ALTER ROLE salafacil_user CREATEDB;` no ambiente
local. Não altere permissões nem recrie bancos existentes automaticamente.
O usuário precisa conectar ao banco de manutenção `postgres` para criar o banco
temporário. Ajustes de autenticação do PostgreSQL devem preservar acesso por senha.

## 3. Comandos de desenvolvimento

Execute na raiz com o ambiente virtual ativo:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
python manage.py migrate --plan
# Somente após conferir o banco de destino e as migrations pendentes:
python manage.py migrate
python manage.py runserver
```

Acesso local: `http://127.0.0.1:8000/`. Para administrar salas, crie um usuário
administrador com `python manage.py createsuperuser` e use `/admin/`.
Respeite os domínios de e-mail aceitos também no cadastro do administrador.
Não crie migrations quando não houver alteração de modelos e não reescreva
migrations já aplicadas sem analisar o impacto.

## 4. Testes e validação

```bash
python manage.py test
python manage.py test accounts bookings core
python manage.py test accounts.tests.RecuperacaoSenhaTests
python manage.py test bookings.tests.ReservaServiceTests
python manage.py test core.tests.DetalhesReservaTests
```

O runner padrão Django descobre 107 testes: 22 em accounts, 28 em bookings,
32 em core e 25 em config. `rooms/tests.py` é apenas um esqueleto sem testes.
Não há pytest, fixtures externas ou serviço de e-mail necessário para a suíte.

O Django cria `test_salafacil`, aplica as migrations e remove esse banco ao fim.
Nunca use esse nome para dados importantes. Antes da primeira execução, confirme
que um banco preexistente com esse nome pode ser usado exclusivamente em testes.
Não autorize sua exclusão automaticamente. `--noinput` só é adequado quando essa
condição já foi verificada, pois pode remover um banco de testes preexistente.

Limitação conhecida: `python manage.py test config` executa 25 testes sem criar
banco e resulta em 24 aprovados/1 falha. `BancoDeDadosTests.test_configuracao_postgres`
espera `test_salafacil`, mas nessa execução isolada o nome continua `salafacil`.
É uma dependência do teste em relação à execução da suíte com banco; não altere
settings ou testes apenas para mascará-la.

Os testes cobrem cadastro, recuperação de senha, filtros, privacidade da
finalidade, criação/conflitos/cancelamento de reservas e endpoints. A prevenção
de concorrência usa transações e bloqueio de linha no serviço, mas não há teste
com transações concorrentes reais. Não interprete a suíte como validação manual
de responsividade, acessibilidade ou envio SMTP real.

## 7. Situação conhecida

Há código para cadastro, login/logout, recuperação de senha, agenda por data,
filtro por tipo de sala, detalhes, reservas, listagem própria e cancelamento.
RF12 e RF13 registram confirmações e cancelamentos a partir de `bookings.0002`
e os exibem em Notificações. O histórico anterior não gera eventos retroativos.
O RF14 permite silenciar os avisos e ocultar o contador por conta. A lista de
notificações continua recebendo os eventos de reserva.
RF15 e RF16 incluem **Minha conta**, com edição de nome e sobrenome, **Avisos de
reservas** e **Preferências da agenda** em Configurações.
RF17, RF18 e RF20 permanecem no planejamento. Confirme sempre o código e o escopo
com a equipe antes de avançar.

Na inspeção de 14/11/2026, o `.venv` e o `.env` já existiam; todas as dependências
fixadas estavam instaladas e `pip check` passou. `manage.py check` passou, não
houve alterações de modelos detectadas e todas as migrations estavam aplicadas.
O banco `salafacil` foi acessado como `salafacil_user`, com CREATEDB habilitado.
`python manage.py test --noinput` executou os 74 testes com sucesso (3,757 s),
criando e removendo o banco temporário. Nenhuma migration foi criada ou aplicada
ao banco de desenvolvimento durante essa preparação. Não foi necessário reinstalar
dependências nem modificar código de aplicação ou testes.
O sandbox bloqueou a conexão inicial; a consulta fora do sandbox funcionou.
Nesses casos, não conclua que o serviço está parado sem testar a restrição de acesso.
