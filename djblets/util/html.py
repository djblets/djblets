"""HTML-related utilities."""

from django.utils.functional import lazy
from django.utils.safestring import SafeString, mark_safe


#: Lazily mark text as safe.
#:
#: This is useful if you need a lazily-translated string (such as with
#: :py:func:`~django.utils.translation.gettext_lazy`) to be marked safe.
#:
#: Args:
#:     text (str):
#:         The text to mark safe.
#:
#: Returns:
#:     django.utils.functional.Promise:
#:     A promise representing the safe text.
mark_safe_lazy = lazy(mark_safe, SafeString)
