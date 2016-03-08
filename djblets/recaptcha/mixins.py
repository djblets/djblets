"""Mixins for providing reCAPTCHA validation support in forms.

See :ref:`using-recaptcha` for a guide on using reCAPTCHA validation.
"""

from __future__ import unicode_literals

import json
import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.six.moves.urllib.error import URLError
from django.utils.six.moves.urllib.parse import urlencode
from django.utils.six.moves.urllib.request import urlopen
from django.utils.translation import ugettext as _

from djblets.recaptcha.widgets import RecaptchaWidget


class RecaptchaFormMixin(forms.Form):
    """A form mixin for providing reCAPTCHA verification.

    If other mixins are used, this should be the first in the list of base
    classes to ensure the reCAPTCHA field is the last.

    Users of this mixin must set the :py:attr:`request` attribute as the
    current :py:class:`~django.http.HttpRequest` instance before
    :py:meth:`clean` is called.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mixin.

        Args:
            *args (tuple):
                Additional positional arguments to pass to the superclass
                constructor.

            **kwargs (dict):
                Additional keyword arguments to pass to the superclass
                constructor.
        """
        super(RecaptchaFormMixin, self).__init__(*args, **kwargs)
        self.fields['g-recaptcha-response'] = forms.CharField(
            required=False,
            widget=RecaptchaWidget)

    @property
    def verify_recaptcha(self):
        """Whether or not the reCAPTCHA is to be verified.

        Returns:
            bool
            Whether or not the reCAPTCHA is to be verified.
        """
        return True

    def clean(self):
        if self.verify_recaptcha:
            recaptcha_response = self.cleaned_data.get('g-recaptcha-response')

            if not recaptcha_response:
                raise ValidationError([
                    _("You must verify that you're not a robot by clicking "
                      "\"'I'm not a robot.\"")
                ])

            data = urlencode({
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': recaptcha_response,
                'remote-ip': self.request.META.get('REMOTE_ADDR'),
            })

            try:
                resp = urlopen(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data)

                payload = resp.read()
            except URLError as e:
                logging.exception('Could not make reCAPTCHA request: HTTP %s: '
                                  '%s',
                                  e.code, e.read())
                raise ValidationError([
                    _('Could not validate reCAPTCHA. Please contact an '
                      'administrator.'),
                ])

            try:
                payload = json.loads(payload)
            except ValueError:
                logging.exception('Could not parse JSON payload from %r',
                                  payload)
                raise ValidationError([
                    _('Could not validate reCAPTCHA. Please contact an '
                      'administrator.'),
                ])

            try:
                if not payload['success']:
                    raise ValidationError([
                        _('Invalid reCAPTCHA response.'),
                    ])
            except KeyError:
                logging.exception('No "success" key in reCAPTCHA payload %r',
                                  payload)
                raise ValidationError([
                    _('Could not validate reCAPTCHA. Please contact an '
                      'administrator.'),
                ])

        return super(RecaptchaFormMixin, self).clean()
