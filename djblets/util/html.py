"""HTML-related utilities."""

from __future__ import unicode_literals

from django.utils import six
from django.utils.functional import lazy
from django.utils.safestring import mark_safe


#: Lazily mark text as safe.
#:
#: This is useful if you need a lazily-translated string (such as with
#: :py:func:`~django.utils.translation.ugettext_lazy`) to be marked safe.
#:
#: Args:
#:     text (six.text_type):
#:         The text to mark safe.
#:
#: Returns:
#:     django.utils.functional.Promise:
#:     A promise representing the safe text.
mark_safe_lazy = lazy(mark_safe, six.text_type)
