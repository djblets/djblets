"""Resource registration and lookup."""

from __future__ import unicode_literals

import logging

from django.utils import six


logger = logging.getLogger(__name__)


_model_to_resources = {}
_name_to_resources = {}
_class_to_resources = {}


class ResourcesRegistry(object):
    """Manages a registry of instances of API resources.

    This handles dynamically loading API resource instances upon request, and
    registering those resources with models.

    When accessing a resource through this class for the first time, it will be
    imported from the proper file and cached. Subsequent requests will be
    returned from the cache.

    While an optional class, consumers are encouraged to create a subclass of
    this that they use for all resource instance references and for registering
    model to resource mappings.
    """

    #: A list of Python module paths to search for module instances.
    #:
    #: When looking up a module, the class will attempt to load a
    #: "<resource_name>_resource" module from that path, with a
    #: "<resource_name>" instance from the module.
    resource_search_path = None

    def __init__(self):
        self._loaded = False

    def __getattr__(self, name):
        """Return a resource instance as an attribute.

        If the resource hasn't yet been loaded into cache, it will be imported,
        fetched from the module, and cached. Subsequent attribute fetches for
        this resource will be returned from the cache.

        Args:
            name (unicode): The name of the resource to look up.

        Returns:
            WebAPIResource:
            The resource instance matching the name.
        """
        if not self._loaded:
            self._loaded = True
            self.register_resources()

        if name not in self.__dict__:
            instance_name = '%s_resource' % name
            found = False

            for search_path in self.resource_search_path:
                try:
                    mod = __import__('%s.%s' % (search_path, name),
                                     {}, {}, [instance_name])
                    self.__dict__[name] = getattr(mod, instance_name)
                    found = True
                    break
                except (ImportError, AttributeError) as e:
                    pass

            if not found:
                logger.exception('Unable to load webapi resource %s: %s',
                                 name, e)
                raise AttributeError('%s is not a valid resource name' % name)

        return self.__dict__[name]

    def register_resources(self):
        """Register model to resource mappings.

        Subclasses must override this to do any registration they may need.
        """
        raise NotImplementedError


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

    cls = obj.__class__

    # Deferred models are a subclass of the actual model that we want to look
    # up.
    if getattr(obj, '_deferred', False):
        cls = cls.__bases__[0]

    resource = _model_to_resources.get(cls, None)

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
