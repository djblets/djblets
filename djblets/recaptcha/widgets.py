from __future__ import unicode_literals

from django.conf import settings
from django.forms import widgets
from django.utils.html import format_html


class RecaptchaWidget(widgets.Widget):
    """A widget for rendering the reCAPTCHA form field."""

    def render(self, *args, **kwargs):
        """Render the reCAPTCHA form field.

        Args:
            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            django.utils.safestring.SafeText:
            The rendered reCAPTCHA widget.
        """
        return format_html(
            '<div class="g-recaptcha" data-sitekey="{0}"></div>',
            settings.RECAPTCHA_PUBLIC_KEY)
