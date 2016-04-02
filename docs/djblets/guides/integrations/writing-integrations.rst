.. _writing-integrations:

====================
Writing Integrations
====================

Overview
========

Integrations are classes that contain some metadata on the integration (name,
icons, description) and perform some initialization (usually listening for
signals and reacting to them).

There's only ever one instance of an integration, but there may be many
configurations, which can contain settings specific to that integration. When
an integration is ready to communicate with some service, it can loop through
these configurations to determine which apply to the event, and can then
use those settings in its communication with the service.

This will be covered in more detail below.


Writing Your Integration
========================

Your integration will usually be a subclass of
:py:class:`~djblets.integrations.integration.Integration`. Each will also
have a subclass of
:py:class:`~djblets.integrations.forms.IntegrationConfigForm` for managing
the configuration of this integration.

.. note::

   Some applications, such as `Review Board`_, have more specific subclasses
   you should inherit from. For instance, Review Board uses
   :py:class:`reviewboard.integrations.Integration` and
   :py:class:`reviewboard.integrations.forms.IntegrationConfigForm`.

   If you're writing integrations for a third-party application, check their
   documentation first.

These integrations will provide a human-readable name, short description,
default settings, a configuration form class, icon URLs, and will perform
initialization.

A typical integration may look like this:

.. code-block:: python

   from django import forms
   from django.contrib.staticfiles.templatetags.staticfiles import static
   from djblets.integrations.forms import IntegrationConfigForm
   from djblets.integrations.integration import Integration


   class MyIntegrationConfigForm(IntegrationConfigForm):
       endpoint_url = forms.CharField(label='Endpoint URL', required=True)
       client_id = forms.CharField(label='Client ID', required=True)


   class MyIntegration(Integration):
       name = 'My Integration'
       description = 'This is my special integration that does stuff.'

       default_settings = {
           'endpoint_url': 'https://example.com/endpoint/',
           'client_id': 'abc123',
       }

       config_form_cls = MyIntegrationConfigForm

       @cached_property
       def icon_static_urls(self):
           return {
               '1x': static('images/my-integration/logo.png'),
               '2x': static('images/my-integration/logo@2x.png'),
           }

       def initialize(self):
           # Here's where you'll begin listening to events.
           pass


That's not too bad, right? Let's break this down into pieces.


.. _Review Board: https://www.reviewboard.org/


Configuration Form
------------------

Your configuration form is what a user will interact with when configuring an
integration. This will come with some default fields for giving the
configuration a short description and enabling/disabling the integration.

You will most likely want to add additional fields. This is just a standard
:py:mod:`Django form <django.forms>`, so you can include anything you want
here. Any fields you add will automatically save in the configuration's
settings, using the field name and cleaned value from the form.

Each field should also have a corresponding default value in the
:py:attr:`~djblets.integrations.integration.Integration.default_settings`
attribute of your integration.

You will need to define a ``Meta`` class containing a ``fieldsets`` attribute.
This is used to specify which fields will be visible and in what order. You
can also include a helpful description for the user, or a title. See the
:py:attr:`~django.contrib.admin.ModelAdmin.fieldsets` documentation for
more information on the format.

.. code-block:: python

   class MyIntegrationConfigForm(IntegrationConfigForm):
       endpoint_url = forms.CharField(label='Endpoint URL', required=True)
       client_id = forms.CharField(label='Client ID', required=True)

       class Meta:
           fieldsets = (
               (None, {
                   'description': (
                       'Some useful instructions for the integration. This '
                       'is a good place to tell them what info to gather '
                       'from another service.'
                   ),
                   'fields': ('endpoint_url', 'client_id'),
               }),
           )


Your form can perform validation and can normalize any user-provided data
through the standard
:ref:`Django Form validation <django:form-and-field-validation>` support.


Integration Metadata
--------------------

Your integration class must set some data to identify itself. There's a
handful of options available:

:py:attr:`~djblets.integrations.integration.Integration.integration_id`:
   A unique identifier for this integration. By default, this is generated for
   you based on the class name and module path.

   If you set it by hand, make sure it contains some uniquely-identifying
   information, such as your company name and product. That can be useful if
   you expect your integration's class name or module path to change at any
   point.

:py:attr:`~djblets.integrations.integration.Integration.name`:
    The name of your integration, which will be shown when listing and
    configuring integrations.

:py:attr:`~djblets.integrations.integration.Integration.description`:
    A short description of your integration, which will also be shown when
    listing integrations.

:py:attr:`~djblets.integrations.integration.Integration.config_form_cls`:
    The configuration form class that you created above. Djblets will take
    care of showing this form when configuring the integration.

:py:attr:`~djblets.integrations.integration.Integration.default_settings`:
    A dictionary of default settings you want for a configuration. You
    should ideally have a default for every setting you'll be working with,
    otherwise you'll have to be careful when looking up data from the
    configuration.

:py:attr:`~djblets.integrations.integration.Integration.icon_static_urls`:
    A dictionary of icon resolution indicators to URLs. This allows you
    to define icons for your integration, and supports high-DPI icons.

    You'll usually want to use
    :py:func:`~django.contrib.staticfiles.templatetags.staticfiles.static`,
    as shown in the example above. However, if your integration is provided
    by an extension, you'll instead want to do:

    .. code-block:: python

       @cached_property
       def icon_static_urls(self):
           extension = MyExtension.instance

           return {
               '1x': extension.get_static_url('images/logo.png'),
               '2x': extension.get_static_url('images/logo@2x.png'),
           }


Handling Initialization
-----------------------

Your integration is most likely going to need to listen to events (such as
:py:class:`Django signals <django.dispatch.Signal>`), in order to know
when to talk to a service. You can do this by making use of a
:py:class:`~djblets.extensions.hooks.SignalHook`, like so:

.. code-block:: python

   from djblets.extensions.hooks import SignalHook
   from djblets.integrations.integration import Integration


   class MyIntegration(Integration):
       def initialize(self):
           SignalHook(self, my_signal, self._on_my_signal)

       def _on_my_signal(self):
           # Handle things here.
           pass


Integrations can actually make use of any built-in extension hooks, and most
third-party hooks.


Querying Configurations
-----------------------

Once you've written your initialization code and began listening for events,
you'll probably want to do something with those events, such as crafting a
message to another service.

Since integrations are designed to work with user-specified configurations,
you'll need to look those up and operate based on them. At a minimum, you're
only going to want to work with configurations that are enabled.

There's a handy function,
:py:meth:`~djblets.integrations.integration.Integration.get_configs`, that
will do the hard work of looking up the configurations. You can use it like
this:

.. code-block:: python

   class MyIntegration(Integration):
       def initialize(self):
           SignalHook(self, my_signal, self._on_my_signal)

       def _on_my_signal(self):
           for config in self.get_configs():
               # Do something with this configuration.
               pass


In the body of the ``for`` loop, you can check the settings for each
configuration and determine if you want to work with it. For example, maybe
the configuration has a setting stating whether it should send a message to a
given IRC channel only if the event has some particular flag set. You can
compare the event's flag to the setting, and skip the configuration if not
set.


Registering Your Integration
----------------------------

Once you have an integration, you'll need to register it.

If your integration is built into your codebase, and not provided by an
extension, then you'll first need to know how your application serves up an
instance of :py:class:`~djblets.integrations.manager.IntegrationManager`, and
then you'll need to call
:py:meth:`~djblets.integrations.manager.IntegrationManager.register_integration_class`:

.. code-block:: python

   get_integration_manager().register_integration_class(MyIntegration)


If your integration is provided by an extension, then you'll want to tie its
registration to the extension. The application should provide a subclass of
:py:class:`~djblets.integrations.hooks.BaseIntegrationHook` for you, which you
can use like this:

.. code-block:: python

   class MyExtension(Extension):
       def initialize(self):
           IntegrationHook(self, MyIntegration)


And that's it. Your integration should be ready to go, and should show up in
the application's list of integrations! Now you get to do the fun work of
actually integrating with whatever service you're targeting. That will be left
as an exercise to the reader.
