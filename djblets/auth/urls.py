"""URL definitions for the djblets.auth app."""

from __future__ import annotations

from django.urls import path

from djblets.auth.views import register


urlpatterns = [
    path('register/', register, kwargs={'next_page': 'test'},
         name='register'),
]
