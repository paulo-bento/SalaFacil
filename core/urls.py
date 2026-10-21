
from django.conf import settings
from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
]

if settings.DEBUG:
    urlpatterns += [
        path("preview/agenda/", views.agenda_preview, name="agenda_preview"),
    ]
