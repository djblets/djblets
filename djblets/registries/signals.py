"""Signals for being notified on registry operations."""

from django.dispatch import Signal


#: Emitted when a registry is populating.
#:
#: Args:
#:     registry (djblets.registries.registry.Registry):
#:         The registry being populated.
registry_populating = Signal()
