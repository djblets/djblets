"""Base support and implementations for extension hooks.

Extension hooks allow applications to define formal ways to inject logic,
behavior, or more into part of the application.

This module provides the base support for defining an extension hook, through
:py:class:`ExtensionHook` and :py:class:`ExtensionHookPoint`, along with
a utility mixin, :py:class:`AppliesToURLMixin`.

It also provides some built-in hooks for applications and extensions to use:

* :py:class:`DataGridColumnsHook`
* :py:class:`SignalHook`
* :py:class:`TemplateHook`
* :py:class:`URLHook`
"""

from __future__ import annotations

import logging
import uuid
from typing import (Any, Callable, Dict, Generic, List, Optional,
                    Sequence, TYPE_CHECKING, Type, cast)

from django.dispatch import Signal
from django.http import HttpRequest
from django.template import Context
from django.template.loader import render_to_string
from django.urls import URLPattern

from djblets.datagrid.grids import Column, DataGrid
from djblets.extensions.extension import Extension
from djblets.registries.registry import Registry, RegistryItemType


logger = logging.getLogger(__name__)


class ExtensionHook:
    """The base class for a hook into some part of an application.

    ExtensionHooks are classes that can hook into an
    :py:class:`ExtensionHookPoint` to provide some level of functionality in an
    application. A consuming application should provide a subclass of
    ExtensionHook that will provide functions for getting data or anything else
    that's needed. Extensions may then subclass or initialize that specific
    ExtensionHook.

    A base ExtensionHook subclass must use :py:class:`ExtensionHookPoint`
    as a metaclass. All hooks deriving from that subclass will be registered
    along with that hook point.

    Example:
        .. code-block:: python

           from djblets.extensions.hooks import (ExtensionHook,
                                                 ExtensionHookPoint)

           from myproject.nav import register_thing, unregister_thing_id


           class ThingHook(ExtensionHook, metaclass=ExtensionHookPoint):
               def initialize(self, thing_id):
                   self.thing_id = thing_id
                   register_thing(self.thing_id)

               def shutdown(self):
                   unregister_thing(self.thing_id)

    .. versionchanged:: 1.0

       Starting with Djblets 1.0, extension hooks should implement the
       :py:meth:`initialize` method to handle any initialization. It no longer
       needs to call the parent :py:meth:`shutdown` method, either. However,
       to retain compatibility with older versions, they may still override
       :py:meth:`__init__` and may call the parent :py:meth:`shutdown`. See
       those methods for more details.

    Attributes:
        extension (djblets.extensions.extension.Extension):
            The parent extension, or another object that can act as a
            hook owner.

        hook_state (int):
            The state of the hook. This will be one of
            :py:data:`HOOK_STATE_DISABLED`, :py:data:`HOOK_STATE_ENABLED`,
            :py:data:`HOOK_STATE_DISABLING`, or :py:data:`HOOK_STATE_ENABLING`.
    """

    #: The hook is disabled.
    HOOK_STATE_DISABLED = 0

    #: The hook is enabled.
    HOOK_STATE_ENABLED = 1

    #: The hook is in the process of disabling.
    HOOK_STATE_DISABLING = 2

    #: The hook is in the process of enabling.
    HOOK_STATE_ENABLING = 3

    remove_hook: Callable[['ExtensionHook', ExtensionHook], None]

    def __init__(
        self,
        extension: Extension,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the ExtensionHook.

        This is called when creating an instance of the hook. This will
        call :py:meth:`enable_hook` with the provided arguments, beginning
        the internal initialization process. That will then call
        :py:meth:`initialize`, which is responsible for any initialization
        of state in the subclass.

        Subclasses should override :py:meth:`initialize` in order to provide
        any state initialization, rather than overriding this method.

        .. versionchanged:: 1.0

           Prior to Djblets 1.0, initialization all happened in
           :py:meth:`__init__`. Code that needs to remain compatible with
           older versions should continue to do so, but otherwise this code
           should move to :py:meth:`initialize`.

        Args:
            extension (djblets.extensions.extension.Extension):
                The parent extension, or another object that can act as a
                hook owner.

            start_enabled (bool, optional):
                Whether to enable the hook once constructed. This defaults
                to ``True``.
        """
        self.extension = extension
        self.hook_state = self.HOOK_STATE_DISABLED

        if kwargs.pop('start_enabled', True):
            self.enable_hook(*args, **kwargs)

    @property
    def initialized(self) -> bool:
        """Whether the hook is initialized and enabled.

        Type:
            bool
        """
        return self.hook_state == self.HOOK_STATE_ENABLED

    def initialize(self, *args, **kwargs) -> None:
        """Initialize the extension hook's state.

        Extension subclasses can perform any custom initialization they need
        here.

        Any additional arguments passed to the hook during construction will be
        passed to this as well.

        While in this function, :py:attr:`hook_state` will be set to
        :py:data:`HOOK_STATE_ENABLING`.

        By default, this does nothing.

        .. versionadded:: 1.0

        Args:
            *args (tuple):
                The list of additional arguments used to initialize the
                hook state.

            **kwargs (dict):
                The additional keyword arguments used to initialize the hook
                state.

        Example:
            .. code-block:: python

               class ThingHook(ExtensionHook, metaclass=ExtensionHookPoint):
                   def initialize(self, thing_id):
                       self.thing_id = thing_id
                       register_thing(self.thing_id)
        """
        pass

    def shutdown(self) -> None:
        """Shut down the extension.

        Extension subclasses can perform any custom cleanup they need here.

        While in this function, :py:attr:`hook_state` will be set to
        :py:data:`HOOK_STATE_DISABLING`.

        .. versionchanged:: 1.0

           This method used to be responsible both for internal cleanup and the
           cleanup of the subclass. Starting in Djblets 1.0, internal cleanup
           has moved to :py:meth:`disable_hook`. Subclasses no longer
           need to call the parent method unless inheriting from a mixin or
           another :py:class:`ExtensionHook` subclass, but should continue to
           do so if they need to retain compatibility with older versions.

        Example:

            .. code-block:: python

               class ThingHook(ExtensionHook, metaclass=ExtensionHookPoint):
                   def shutdown(self):
                       unregister_thing(self.thing_id)
        """
        assert self.hook_state != self.HOOK_STATE_ENABLED

    def enable_hook(self, *args, **kwargs) -> None:
        """Enable the ExtensionHook, beginning the initialization process.

        This will register the instance of the hook and begin its
        initialization. It takes the same parameters that would be given
        during construction of the hook, allowing disabled hooks to be
        created again with fresh state.

        Subclasses should not override this process. They should instead
        implement :py:meth:`initialize` to handle initialization of the
        state of the hook.

        .. versionadded:: 1.0

        Args:
            *args (tuple):
                The list of additional arguments used to initialize the
                hook state.

            **kwargs (dict):
                The additional keyword arguments used to initialize the hook
                state.
        """
        assert self.hook_state == self.HOOK_STATE_DISABLED

        self.hook_state = self.HOOK_STATE_ENABLING
        self.extension.hooks.add(self)
        cast(ExtensionHookPoint, self.__class__).add_hook(self)

        self.initialize(*args, **kwargs)
        self.hook_state = self.HOOK_STATE_ENABLED

    def disable_hook(
        self,
        call_shutdown: bool = True,
    ) -> None:
        """Disable the hook, unregistering it from the extension.

        This will unregister the hook and uninitialize it, putting it into
        a disabled state.

        Consumers can call this if they want to turn off hooks temporarily
        without reconstructing the instances later. It's also called
        internally when shutting down an extension.

        .. versionadded:: 1.0

        Args:
            call_shutdown (bool, optional):
                Whether to call :py:meth:`shutdown`. This should always be
                ``True`` unless called internally.
        """
        assert self.hook_state == self.HOOK_STATE_ENABLED

        self.hook_state = self.HOOK_STATE_DISABLING

        if call_shutdown:
            self.shutdown()

        cast(ExtensionHookPoint, self.__class__).remove_hook(self)
        self.hook_state = self.HOOK_STATE_DISABLED


class ExtensionHookPoint(type):
    """A metaclass used for base Extension Hooks.

    Base :py:class:`ExtensionHook` classes use :py:class:`ExtensionHookPoint`
    as a metaclass. This metaclass stores the list of registered hooks that
    an :py:class:`ExtensionHook` will automatically register with.
    """

    def __init__(cls, name, bases, attrs):
        super(ExtensionHookPoint, cls).__init__(name, bases, attrs)

        if not hasattr(cls, 'hooks'):
            cls.hooks = []

    def add_hook(cls, hook):
        """Adds an ExtensionHook to the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.append(hook)

    def remove_hook(cls, hook):
        """Removes an ExtensionHook from the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.remove(hook)


if TYPE_CHECKING:
    MixinParent = Extension
else:
    MixinParent = object


class AppliesToURLMixin(MixinParent):
    """A mixin for hooks to allow restricting to certain URLs.

    This provides an :py:meth:`applies_to` function for the hook that can be
    used by consumers to determine if the hook should apply to the current
    page.
    """

    def initialize(
        self,
        apply_to: List[str] = [],
        *args,
        **kwargs,
    ) -> None:
        """Initialize the mixin for a hook.

        Args:
            apply_to (list, optional):
                A list of URL names that the hook will apply to by default.
        """
        self.apply_to = apply_to

        super().initialize(*args, **kwargs)

    def applies_to(
        self,
        request: HttpRequest,
    ) -> bool:
        """Return whether or not this hook applies to the page.

        This will determine whether any of the URL names provided in
        ``apply_to`` matches the current requested page.

        Args:
            request (django.http.HttpRequest):
                The request object.

        Returns:
            bool:
            Whether this hook applies to the page currently being rendered.
        """
        return (not self.apply_to or
                (request.resolver_match is not None and
                 request.resolver_match.url_name in self.apply_to))


class DataGridColumnsHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """Adds columns to a datagrid.

    This hook allows an extension to register new columns to any datagrid.
    These columns can be added by the user, rearranged, and sorted, like
    any other column.

    Each column must have an id already set, and it must be unique.
    """

    def initialize(
        self,
        datagrid_cls: Type[DataGrid],
        columns: List[Column],
    ) -> None:
        """Initialize the hook.

        Args:
            datagrid_cls (type):
                The specific datagrid class that will include this
                registered list of columns as possible options.

            columns (list):
                A list of :py:class:`~djblets.datagrid.grids.Column`
                instances to register on the datagrid.
        """
        self.datagrid_cls = datagrid_cls
        self.columns = columns

        for column in columns:
            self.datagrid_cls.add_column(column)

    def shutdown(self) -> None:
        """Shut down the hook."""
        for column in self.columns:
            self.datagrid_cls.remove_column(column)


class URLHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """Custom URL hook.

    A hook that installs custom URLs. These URLs reside in a project-specified
    parent URL.
    """

    def initialize(
        self,
        patterns: List[URLPattern],
    ) -> None:
        """Initialize the hook.

        Args:
            patterns (list):
                The list of :py:func:`~django.urls.path` entries
                comprising the URLs to register.
        """
        self.patterns = patterns
        self.dynamic_urls = self.extension.extension_manager.dynamic_urls
        self.dynamic_urls.add_patterns(patterns)

    def shutdown(self) -> None:
        self.dynamic_urls.remove_patterns(self.patterns)


class SignalHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """Connects to a Django signal.

    This will handle connecting to a signal, calling the specified callback
    when fired. It will disconnect from the signal when the extension is
    disabled.

    The callback will also be passed an extension= keyword argument pointing
    to the extension instance.
    """

    def initialize(
        self,
        signal: Signal,
        callback: Callable,
        sender: Any = None,
        sandbox_errors: bool = True,
    ) -> None:
        """Initialize the hook.

        Args:
            signal (django.dispatch.Signal):
                The signal to connect to.

            callback (callable):
                The function to call when the signal is fired.

            sender (object or class, optional):
                The sender argument to pass to the signal connection.
                See :py:meth:`~django.core.dispatch.Signal.send` for more
                information.

            sandbox_errors (bool, optional):
                If ``True``, errors coming from ``callback`` will be
                sandboxed, preventing them from reaching the code that
                fired the signal. The error will instead be logged and
                then ignored.
        """
        self.signal = signal
        self.callback = callback
        self.dispatch_uid = uuid.uuid1()
        self.sender = sender
        self.sandbox_errors = sandbox_errors

        signal.connect(self._wrap_callback, sender=self.sender, weak=False,
                       dispatch_uid=str(self.dispatch_uid))

    def shutdown(self) -> None:
        """Shut down the hook."""
        self.signal.disconnect(dispatch_uid=str(self.dispatch_uid),
                               sender=self.sender)

    def _wrap_callback(self, **kwargs) -> None:
        """Wrap a callback function, passing extra parameters and sandboxing.

        This will call the callback with an extension= keyword argument,
        and sandbox any errors (if sandbox_errors is True).

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the callback.
        """
        try:
            self.callback(extension=self.extension, **kwargs)
        except Exception as e:
            logger.exception('Error when calling %r from SignalHook: %s',
                             self.callback, e)

            if not self.sandbox_errors:
                raise


class TemplateHook(AppliesToURLMixin, ExtensionHook,
                   metaclass=ExtensionHookPoint):
    """Custom templates hook.

    A hook that renders a template at hook points defined in another template.
    """

    _by_name: Dict[str, List[TemplateHook]] = {}

    ######################
    # Instance variables #
    ######################

    #: The name of the hook point to attach to.
    #:
    #: Type:
    #:     str
    name: str

    #: The name of the template file to render.
    #:
    #: Type:
    #:     str
    template_name: Optional[str]

    #: Any additional context to use when rendering.
    #:
    #: Type:
    #:     dict
    extra_context: dict

    def initialize(
        self,
        name: str,
        template_name: Optional[str] = None,
        apply_to: List[str] = [],
        extra_context: Dict[str, Any] = {},
        *args,
        **kwargs,
    ) -> None:
        """Initialize the hook.

        Args:
            name (str):
                The name of the template hook point that should render this
                template. This is application-specific.

            template_name (str, optional):
                The name of the template to render.

            apply_to (list, optional):
                The list of URL names where this template should render.
                By default, all templates containing the template hook
                point will render this template.

            extra_context (dict):
                Extra context to include when rendering the template.

            *args (tuple):
                Additional positional arguments for future expansion.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        super().initialize(apply_to=apply_to)

        self.name = name
        self.template_name = template_name
        self.extra_context = extra_context

        if name not in self.__class__._by_name:
            self.__class__._by_name[name] = [self]
        else:
            self.__class__._by_name[name].append(self)

    def shutdown(self) -> None:
        self.__class__._by_name[self.name].remove(self)

    def render_to_string(
        self,
        request: HttpRequest,
        context: Context,
    ) -> str:
        """Render the content for the hook.

        By default, this renders the provided template name to a string
        and returns it.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            context (django.template.Conetxt):
                The template render context.

        Returns:
            str:
            Rendered content to include in the template.
        """
        context_data = {
            'extension': self.extension,
        }
        context_data.update(self.get_extra_context(request, context))
        context_data.update(self.extra_context)

        # Note that context.update implies a push().
        context.update(context_data)

        assert self.template_name is not None
        s = render_to_string(template_name=self.template_name,
                             context=context.flatten(),
                             request=request)

        context.pop()

        return s

    def get_extra_context(
        self,
        request: HttpRequest,
        context: Context,
    ) -> Dict[str, Any]:
        """Return extra context for the hook.

        Subclasses can override this to provide additional context
        dynamically beyond what's passed in to the constructor.

        By default, an empty dictionary is returned.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            context (django.template.Context):
                The template render context.

        Returns:
            dict:
            Additional context to include when rendering the template.
        """
        return {}

    @classmethod
    def by_name(
        cls,
        name: str,
    ) -> List[TemplateHook]:
        """Return template hooks by name.

        Args:
            name (str):
                The name of the hook point.

        Returns:
            list of TemplateHook:
            A list of all template hooks that are registered for the given
            name.
        """
        return cls._by_name.get(name, [])


class BaseRegistryHook(Generic[RegistryItemType],
                       ExtensionHook):
    """A hook for registering an item with a registry.

    This hook should not be used directly. Instead, it should be subclassed
    with the :py:attr:`registry` attribute set.

    Subclasses must use the :py:class:`ExtensionHookPoint` metaclass.

    Version Changed:
        5.1:
        This hook now supports typed registries.
    """

    #: The registry to register items with.
    registry: Optional[Registry[RegistryItemType]] = None

    ######################
    # Instance variables #
    ######################

    #: The item registered in the registry.
    item: RegistryItemType

    def initialize(
        self,
        item: RegistryItemType,
    ) -> None:
        """Initialize the registry hook with the item.

        Args:
            item (object):
                The object to register.
        """
        self.item = item

        assert self.registry is not None
        self.registry.register(item)

    def shutdown(self) -> None:
        """Shut down the registry hook and unregister the item."""
        assert self.registry is not None
        self.registry.unregister(self.item)


class BaseRegistryMultiItemHook(Generic[RegistryItemType],
                                ExtensionHook):
    """A hook for registering multiple items with a registry.

    This hook should not be used directly. Instead, it should be subclassed
    with the :py:attr:`registry` attribute set.

    Subclasses must use the :py:class:`ExtensionHookPoint` metaclass.

    Version Changed:
        5.1:
        This hook now supports typed registries.
    """

    #: The registry to register items with.
    registry: Optional[Registry[RegistryItemType]] = None

    ######################
    # Instance variables #
    ######################

    #: The items registered in the registry.
    items: Sequence[RegistryItemType]

    def initialize(
        self,
        items: Sequence[RegistryItemType],
    ) -> None:
        """Initialize the registry hook with the list of items.

        Args:
            items (list):
                The list of items to register.
        """
        self.items = items

        registry = self.registry
        assert registry is not None

        registered_items: List[RegistryItemType] = []

        for item in items:
            try:
                registry.register(item)
            except Exception:
                # If there's an error, first unregister all existing items and
                # then re-raise the error.
                for item in registered_items:
                    try:
                        registry.unregister(item)
                    except Exception:
                        pass

                raise

            registered_items.append(item)

    def shutdown(self) -> None:
        """Shut down the registry hook and unregister the items."""
        registry = self.registry
        assert registry is not None

        for item in self.items:
            registry.unregister(item)
