"""Utility functions for looking up static media URLs."""

from django.templatetags.static import static
from django.utils.functional import lazy


#: Lazily look up a static media URL.
#:
#: This is used to reference static media URLs in a class attribute, in a
#: global variable, or some other definition that would be evaluated upon
#: loading the module. Calling :py:func:`~django.templatetags.static`
#: will immediately perform a lookup, which may be too early in the startup
#: sequence of the consuming application. By lazily referencing the URL,
#: the lookup can be performed later when needed, and not on module load.
#:
#: Args:
#:     path (unicode):
#:         The static media path.
#:
#: Returns:
#:     django.utils.functional.__proxy__:
#:     A proxy that evaluates to the static media URL (as a unicode string).
static_lazy = lazy(static, str)
