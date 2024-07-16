"""Authentication-related signals."""

from __future__ import annotations

from django.dispatch import Signal


#: A new user has been registered.
#:
#: This is emitted if using the :py:func:`djblets.auth.views.register` view to
#: register a new user. It can also be emitted by other registration
#: implementations, if useful to the application.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user that was newly registered.
user_registered = Signal()
