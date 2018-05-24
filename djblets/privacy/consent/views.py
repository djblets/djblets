"""View mixins and decorators for requiring consent."""

from __future__ import unicode_literals

from functools import wraps

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

from djblets.privacy.consent.tracker import get_consent_tracker


_CONSENT_REDIRECT_SETTING = 'DJBLETS_PRIVACY_PENDING_CONSENT_REDIRECT_URL'


def check_pending_consent(view):
    """A decorator for ensuring the user has no pending consent requirements.

    If the user does, they will be redirected to
    ``settings.DJBLETS_PRIVACY_PENDING_CONSENT_REDIRECT_URL``.

    Args:
        view (callable):
            The view to decorate

    Returns:
        callable:
        The decorated view.
    """
    @wraps(view)
    def decorated(request, *args, **kwargs):
        tracker = get_consent_tracker()

        if (request.user.is_authenticated() and
            len(tracker.get_pending_consent_requirements(request.user))):
            redirect_url = getattr(settings, _CONSENT_REDIRECT_SETTING, None)

            if redirect_url is None:
                raise ImproperlyConfigured(
                    'settings.%s must be set.' % _CONSENT_REDIRECT_SETTING
                )

            if callable(redirect_url):
                redirect_url = redirect_url(request)

            return HttpResponseRedirect(redirect_url)

        return view(request, *args, **kwargs)

    return decorated


class CheckPendingConsentMixin(object):
    """A view mixin for ensuring the user has no pending consent requirements.

    If the user does, they will be redirected to
    ``settings.DJBLETS_PRIVACY_PENDING_CONSENT_REDIRECT_URL``

    This mixin requires the use of
    :py:class:`~djblets.views.generic.base.PrePostDispatchViewMixin`.
    """

    @method_decorator(check_pending_consent)
    def pre_dispatch(self, *args, **kwargs):
        """Dispatch the request.

        Args:
            *args (tuple):
                Positional arguments from the URL resolver.

            **kwargs (dict):
                Keyword arguments from the URL resolver.

        Returns:
            django.http.HttpResponse:
            Either a redirect or ``None``.
        """
        return super(CheckPendingConsentMixin, self).pre_dispatch(
            *args, **kwargs)
