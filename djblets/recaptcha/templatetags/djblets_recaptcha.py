from __future__ import unicode_literals

from django import template
from django.utils.html import mark_safe


register = template.Library()


@register.simple_tag
def recaptcha_js():
    """Render the reCAPTCHA JavaScript tag.

    Returns:
        django.utils.safestring.SafeText:
        The rendered tag.
    """
    return mark_safe('<script src="https://www.google.com/recaptcha/api.js">'
                     '</script>')


@register.simple_tag
def recaptcha_form_field(form):
    """Return the reCAPTCHA field from the specified form.

    This can be used to render the reCAPTCHA widget.

    Args:
        form (django.forms.forms.Form):
            The form that is being rendered.

    Returns:
        django.forms.boundfield.BoundField:
        The bound reCAPTCHA field. This will render as its widget in a
        template.
    """
    return form['g-recaptcha-response']
