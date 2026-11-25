
from django.conf import settings
from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("minhas-reservas/", views.minhas_reservas, name="minhas_reservas"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("notificacoes/", views.notificacoes, name="notificacoes"),
    path("notificacoes/estado/", views.consultar_estado_notificacoes, name="estado_notificacoes"),
    path("notificacoes/preferencia/", views.salvar_preferencia_notificacoes, name="preferencia_notificacoes"),
    path("notificacoes/ler-todas/", views.ler_todas_notificacoes, name="ler_todas_notificacoes"),
    path("notificacoes/<int:notificacao_id>/ler/", views.ler_notificacao, name="ler_notificacao"),
]

if settings.DEBUG:
    urlpatterns += [
        path("preview/agenda/", views.agenda_preview, name="agenda_preview"),
    ]
