"""Web API signals."""

from django.core.signals import Signal


#: A signal indicating a WebAPI token has been created.
#:
#: Args:
#:     instance (djblets.webapi.models.WebAPIToken):
#:         The created instance.
#:
#:     auto_generated (bool):
#:         Whether or not the token was automatically generated.
webapi_token_created = Signal()


#: A signal indicating an attempt to authenticate with an expired WebAPI token.
#:
#: Version Added:
#:     3.0
#:
#: Args:
#:     instance (djblets.webapi.models.WebAPIToken):
#:         The expired instance.
webapi_token_expired = Signal()


#: A signal indicating a WebAPI token has been updated.
#:
#: Args:
#:     instance (djblets.webapi.models.WebAPIToken):
#:         The updated instance.
webapi_token_updated = Signal()
