"""Import utilities for registries."""

from __future__ import unicode_literals

from importlib import import_module

from djblets.util.compat.django.utils.functional import SimpleLazyObject


def lazy_import_registry(module_path, registry_name, **kwargs):
    """Lazily import and construct a registry on access.

    This is useful for providing registry instances in a Django app's
    :file:`__init__.py` file without needing to import other modules that
    might interfere with the Django initialization process. When accessed
    for the first time, the registry will be imported and constructed.

    This can also speed up the startup process, depending on the complexity
    of registries.

    Args:
        module_path (str):
            The import path of the module containing the registry.

        registry_name (str):
            The class name of the registry.

        **kwargs (dict):
            Keyword arguments to pass to the registry's constructor.

    Returns:
        djblets.util.compat.django.utils.functional.SimpleLazyObject:
        A wrapper that will dynamically load and forward on to the registry.
    """
    def _create_registry():
        mod = import_module(module_path)

        return getattr(mod, registry_name)(**kwargs)

    return SimpleLazyObject(_create_registry)
