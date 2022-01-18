"""URLs for extensions (used in the admin UI)."""

from django.urls import path

from djblets.extensions.views import extension_list


urlpatterns = [
    path('', extension_list, name='extension-list'),
]
