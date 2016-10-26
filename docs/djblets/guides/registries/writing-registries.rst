.. _writing-registries:

==================
Writing Registries
==================

.. currentmodule:: djblets.registries.registry


Overview
--------

Registries are utilities for keeping track of objects. They guarantee that each
element registered with them is unique and do not share any attributes with any
other registered elements. That is, for each attribute the registry defines,
no two registered elements will have the same value for that attribute.


Subclassing Registries
----------------------

Registries are intended to be subclassed. They have attributes that subclasses
should override to customize the behaviour:

* :py:attr:`~Registry.lookup_attrs`, which determine which attributes on the
  elements will be usable as lookup attributes. This should be either a
  :py:class:`tuple` or a :py:class:`list` containing strings of attribute
  names.

  For example

  .. code-block:: python

     class MyRegistry(Registry):
         lookup_attrs = ['id', 'name']

     registry = MyRegistry()

     # Register a new item.
     registry.register(Item(id=0, name='bar'))

     # Look up the item by its attributes.
     assert registry.get('id', 0) is registry.get('name', 'bar')

     # Unregister the item.
     registry.unregister_by('id', 0)

* :py:attr:`~Registry.errors`, which determines the error interpolation strings
  for exceptions raised by the registry. This allows registry subclasses to
  customized and contextualized error messages about the type of item in the
  registry, instead of referring to "item"s.

  These messages override the default error messages, which are defined in the
  :py:data:`DEFAULT_ERRORS` dictionary.

* :py:attr:`~Registry.lookup_error_class`, which determines the exception class
  for item lookup errors (i.e., when an item cannot be found in the registry).
  This should be a subclass of
  :py:class:`~djblets.registries.errors.ItemLookupError`.


Overriding Error Messages
~~~~~~~~~~~~~~~~~~~~~~~~~

The error messages provided by registries are intentionally vague. To give more
specific error messages, the :py:attr:`~Registry.errors` attribute can be
overridden. This attribute provides the error interpolation strings for errors
in the registry.

For example:

.. code-block:: python

   from django.utils.translation import ugettext as _
   from djblets.registries.registry import ALREADY_REGISTERED, Registry

   class FooRegistry(Registry):
        errors = {
             ALREADY_REGISTERED: _(
                'Could not register the foo "%(attr_name)": it is already '
                'registered.',
             ),
        }

If a subclass wishes to provide more default errors, the
:py:attr:`~Registry.default_errors` attribute can be overridden for this
purpose.

For example:

.. code-block:: python

   from django.utils.translation import ugettext as _
   from djblets.registries.errors import DEFAULT_ERRORS as DjbletsDefaultErrors

   HTTP_ERROR = 'http_error'

   DEFAULT_ERRORS = DjbletsDefaultErrors.copy()
   DEFAULT_ERRORS.update({
       HTTP_ERROR: _(
           'There was an HTTP error: %(error)s.',
       ),
   })


   class ApiRegistry(Registry):
       """A registry that persists itself to an API."""

       default_errors = DEFAULT_ERRORS
       api_url = "http://example.com"

       def save(self):
           try:
               update(api_url, list(self))
           except HttpError as e:
               raise Exception(self.format_error(HTTP_ERROR,
                                                 error=e))


Default Item Registration
~~~~~~~~~~~~~~~~~~~~~~~~~

Registries can provide default items to be registered when they are first
accessed. These default items will populate the registry whenever one of the
following methods is called:

* :py:meth:`~Registry.get`
* :py:meth:`~Registry.register`
* :py:meth:`~Registry.unregister`
* :py:meth:`~Registry.unregister_by_attr`
* :py:meth:`~Registry.populate`

The registry will not be populated more than once. They are lazily populated
and will never be populated until one of the above methods is called.

For example:

.. code-block:: Python

   class DefaultItemsRegistry(Registry):
       """A registry that provides default items."""

       def get_defaults(self):
           return [1, 2, 3]


The :py:meth:`~Registry.get_defaults` method can either return an iterable
(such as a :py:class:`list`) or ``yield`` its items, as the result will only
ever be consumed once


Example Registries
------------------

The following examples are practical uses of registries that may be useful
beyond the default definition.


Ordered Registries
~~~~~~~~~~~~~~~~~~

Suppose we wanted to retrieve each item from the registry in the order it was
registered in. We can do that by keeping a list that contains the :py:func:`id`
of each registered item. Then, instead of iterating through the registry in the
default order, we can iterate through in the order the items were registered.

.. code-block:: python

   class OrderedRegistry(Registry):
       """A registry which maintains the order of its items."""

       def __init__(self):
           self._key_order = []
           self._by_id = {}
           super(OrderedRegistry, self).__init__()

       def register(self, item):
           """Register an item and keep track of its insertion order."""
           super(OrderedRegistry, self).register(item)
           self._key_order.append(id(item))
           self._by_id[id(item)] = item

       def unregister(self, item):
           """Unregister an item and remove it from the insertion order."""
           super(OrderedRegistry, self).unregister(item)
           key = id(item)
           del self._by_id[key]
           self._key_order.remove(key)

       def __iter__(self):
           """Yield each registered item in insertion order."""
           for key in self._key_order:
               yield self._by_id[key]


This behavior is available in the :py:class:`OrderedRegistry` class.


Exception-less Registries
~~~~~~~~~~~~~~~~~~~~~~~~~

If :py:meth:`~Registry.get` raising an exception is not useful and instead you
would prefer a sentinel value (e.g., ``None``) to be returned instead, the
:py:meth:`~Registry.get` method could be overridden as in the following
example.

.. code-block:: python

   class SafeRegistry(Registry):
       """A registry that does not throw exceptions on item lookup failure."""

       def get(self, attr_name, attr_value):
           """Return the item if it is registered; otherwise, return None."""
           try:
               return super(SafeRegistry, self).get(attr_name, attr_value)
           except ItemLookupError:
               return None

This behavior is also available as a mixin, as
:py:class:`~djblets.registries.mixins.ExceptionFreeGetterMixin`. It can be used
as follows and is equivalent to the above code example.

.. code-block:: python

   from djblets.registries.mixins import ExceptionFreeGetterMixin

   class SafeRegistry(ExceptionFreeGetterMixin, Registry):
       pass

