"""Web API signals."""

from __future__ import unicode_literals

from django.core.signals import Signal


#: A signal indicating a WebAPI token has been created.
#:
#: Args:
#:     instance (djblets.webapi.models.WebAPIToken):
#:         The created instance.
#:
#:     auto_generated (bool):
#:         Whether or not the token was automatically generated.
webapi_token_created = Signal(providing_args=['instance', 'auto_generated'])


#: A signal indicating a WebAPI token has been updated.
#:
#: Args:
#:     instance (djblets.webapi.models.WebAPIToken):
#:         The updated instance.
webapi_token_updated = Signal(providing_args=['instance'])
