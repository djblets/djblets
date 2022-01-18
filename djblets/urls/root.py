"""URL patterns for applications that can use SITE_ROOT."""

from django.conf import settings
from django.conf.urls import handler404, handler500
from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path


# Ensures that we can run nose on this without needing to set SITE_ROOT.
# Also serves to let people know if they set one variable without the other.
if hasattr(settings, 'SITE_ROOT'):
    if not hasattr(settings, 'SITE_ROOT_URLCONF'):
        raise ImproperlyConfigured('SITE_ROOT_URLCONF must be set when '
                                   'using SITE_ROOT')

    urlpatterns = [
        path('%s' % settings.SITE_ROOT[1:],
             include(settings.SITE_ROOT_URLCONF)),
    ]
else:
    urlpatterns = None


__all__ = [
    'handler404',
    'handler500',
    'urlpatterns',
]
