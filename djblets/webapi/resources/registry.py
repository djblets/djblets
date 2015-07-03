"""Resource registration and lookup."""

from __future__ import unicode_literals

from django.utils import six


_model_to_resources = {}
_name_to_resources = {}
_class_to_resources = {}


def register_resource_for_model(model, resource):
    """Register a resource as the official location for a model.

    Args:
        model (Model):
            The model associated with the resource.

        resource (WebAPIResource or callable):
            Either a WebAPIResource, or a function that takes an instance of
            ``model`` and returns a WebAPIResource.
    """
    _model_to_resources[model] = resource


def unregister_resource_for_model(model):
    """Remove the official location for a model.

    Args:
        model (Model): The model associated with the resource to remove.
    """
    del _model_to_resources[model]


def get_resource_for_object(obj):
    """Return the resource for an object.

    Args:
        obj: The object whose model has a resource associated.

    Returns:
        WebAPIResource:
        The resource associated with the object, or ``None`` if not found.
    """
    from djblets.webapi.resources.base import WebAPIResource

    resource = _model_to_resources.get(obj.__class__, None)

    if not isinstance(resource, WebAPIResource) and six.callable(resource):
        resource = resource(obj)

    return resource


def get_resource_from_name(name):
    """Return the resource of the specified name.

    Args:
        name (unicode): The name of the resource.

    Returns:
        WebAPIResource: The resource instance, or ``None`` if not found.
    """
    return _name_to_resources.get(name, None)


def get_resource_from_class(klass):
    """Return the resource with the specified resource class.

    Args:
        klass (class): The WebAPIResource subclass.

    Returns:
        WebAPIResource: The resource instance, or ``None`` if not found.
    """
    return _class_to_resources.get(klass, None)


def unregister_resource(resource):
    """Unregister a resource from the caches.

    Args:
        resource (WebAPIResource): The resource instance to unregister.
    """
    del _name_to_resources[resource.name]
    del _name_to_resources[resource.name_plural]
    del _class_to_resources[resource.__class__]
