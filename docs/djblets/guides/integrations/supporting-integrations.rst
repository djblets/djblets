.. _supporting-integrations:

=======================
Supporting Integrations
=======================

Overview
========

Integrations provide a friendly way for an application to allow users to
link up with multiple services. An application can provide support for any
number of integrations, and give users a way to manage them. Much of this is
provided out of the box for you, including administration pages, but there are
a few things the application must do in order to support integrations.

This guide will cover everything you need to integrate with the Djblets
Integrations framework.


Architecture
------------

To start with, let's discuss the architecture.

Integrations are subclasses of
:py:class:`~djblets.integrations.integration.Integration`. There's only ever
one instance per class. Each instance may have zero or more configurations,
defined as an application-provided subclass of
:py:class:`~djblets.integrations.models.BaseIntegrationConfig`.

Integrations and configurations are managed by an instance of
:py:class:`~djblets.integrations.manager.IntegrationManager`.

Many classes need to know about the manager instance, which can't be
determined automatically (and, theoretically, there may be multiple managers
in a single application). These classes will inherit from
:py:class:`~djblets.integrations.mixins.NeedsIntegrationManagerMixin`. It's
the application's responsibility to subclass these classes and provide the
necessary method for returning the integration, which we'll get to later.

:py:class:`~djblets.integrations.forms.IntegrationConfigForm` provides UI and
logic for creating or editing integration configurations.

:py:class:`~djblets.integrations.hooks.BaseIntegrationHook` provides base
support for an extension hook, which is useful if you're supporting
:py:ref:`extensions <extension-guides>` in your application.

There are :py:mod:`views <djblets.integrations.views>` for listing and
configuring integrations. These must be subclassed, which we'll cover in more
detail.


Getting Started
===============

Updating Settings
-----------------

First, you'll need to update your Django settings in order to use the
integrations framework.

We're going to assume in these examples that you're creating a new
``myproject.integrations`` app. Put that and ``djblets.integrations`` in your
``settings.INSTALLED_APPS``, like so:

.. code-block:: python

   INSTALLED_APPS = [
       ...
       'djblets.integrations',
       'myproject.integrations',
       ...
   ]


Now add the middleware:

.. code-block:: python

   MIDDLEWARE_CLASSES = [
       ...
       'djblets.integrations.middleware.IntegrationsMiddleware',
       ...
   ]

If you're also using :py:mod:`djblets.extensions`, make sure to include this
*after* the extensions middleware:

.. code-block:: python

   MIDDLEWARE_CLASSES = [
       ...
       'djblets.extensions.middleware.ExtensionsMiddleware',
       'djblets.integrations.middleware.IntegrationsMiddleware',
       ...
   ]


Setting up IntegrationManager
-----------------------------

Your application will need an instance of
:py:class:`~djblets.integrations.manager.IntegrationManager`. This should only
be created once per process, and every request for this manager must receive
the same instance.

When constructing the manager, a subclass of
:py:class:`~djblets.integrations.models.BaseIntegrationConfig` will need to be
provided. We'll go into what's needed here, but keep this in mind for now.

Let's put this in :file:`myproject/integrations/base.py`. You'll want
something like:

.. code-block:: python

   from djblets.integrations.manager import IntegrationManager


   _integration_manager = None


   def get_integration_manager():
       global _integration_manager

       if not _integration_manager:
           _integration_manager = IntegrationManager(MyIntegrationConfig)

       return _integration_manager


You now have a handy function for getting the same instance, and for using
your ``MyIntegrationConfig`` (which you'll create soon).

You're also going to want a mixin that provides this integration manager to
various classes. Add:

.. code-block:: python

   class GetIntegrationManagerMixin(object):
       @classmethod
       def get_integration_manager(self):
           return get_integration_manager()


Congrats, you're one step closer to supporting integrations!


Creating an IntegrationConfig
-----------------------------

:py:class:`~djblets.integrations.models.BaseIntegrationConfig` is the base
class for an integration configuration database model. This stores identifying
information used to associate the configuration with a given integration, a
description of the configuration, the enabled state, settings, and more.

Applications must have a subclass of this in a
:file:`myproject/integrations/models.py`, providing it to the
:py:class:`~djblets.integrations.manager.IntegrationManager` as shown above.
You'll want to mix in your ``GetIntegrationManagerMixin``, like so:

.. code-block:: python

   from djblets.integrations.models import BaseIntegrationConfig

   from myproject.integrations.base import GetIntegrationManagerMixin


   class IntegrationConfig(GetIntegrationManagerMixin, BaseIntegrationConfig):
       pass


That's all you need to do to get started. If you want to add some additional
fields (for example, to associate one of these with a specific user,
organization, etc.), then you can add fields here. For example:


Setting Up Views
----------------

Now that you have the base foundation for integrations and their configuration
and management, you'll need to get some views going.

Djblets ships with base views for listing integrations and creating/editing
configurations. These are
:py:class:`~djblets.integrations.views.BaseIntegrationListView` and
:py:class:`~djblets.integrations.views.BaseIntegrationConfigFormView`.

It also ships with versions intended for use in the administration UI:
:py:class:`~djblets.integrations.views.BaseAdminIntegrationListView` and
:py:class:`~djblets.integrations.views.BaseAdminIntegrationConfigFormView`.

In these examples, we're going to assume you're using views
for the administration UI.

Whichever views you choose to use will need to be subclassed, using your
``GetIntegrationManagerMixin`` above. This is as simple as placing the
following in a :file:`myproject/integrations/views.py`:

.. code-block:: python

   from djblets.integrations.views import (BaseAdminIntegrationConfigFormView,
                                           BaseAdminIntegrationListView)

   from myproject.integrations.base import GetIntegrationManagerMixin


   class AdminIntegrationConfigFormView(GetIntegrationManagerMixin,
                                        BaseAdminIntegrationConfigFormView):
       pass


   class AdminIntegrationListView(GetIntegrationManagerMixin,
                                  BaseAdminIntegrationListView):
       pass


You can customize some other behavior of these views as well. See their
documentation for more information.


Setting up URLs
---------------

Now that you have your views, you'll need to build URLs for them. In this
example, we'll place them in your :file:`myproject/urls.py`:

.. code-block:: python

   from django.conf.urls import include, patterns, url
   from djblets.integrations.urls import build_integration_urlpatterns

   from myproject.integrations.views import (AdminIntegrationConfigFormView,
                                             AdminIntegrationListView)


   urlpatterns = patterns(
       '',

       url('^admin/integrations/', include(build_integration_urlpatterns(
           list_view_cls=AdminIntegrationListView,
           config_form_view_cls=AdminIntegrationConfigFormView))),

       ...
   )

You should now be set! If you go to ``http://yourserver/admin/integrations/``,
you should see a list of all your integrations (none, at this moment), and
will have UI for configuring them.

You can now start :ref:`writing integrations <writing-integrations>`.


Advanced Usage
==============

Adding Fields to IntegrationConfig
----------------------------------

You may want to add some special fields to your configuration model. For
instance, you may want to associate it with a user, or an organization model,
or maybe you want to store something else entirely.

To do this, you'll first need to add the fields to your configuration model.
We'll show this off with a User association:

.. code-block:: python

   from django.contrib.auth.models import User
   from djblets.integrations.models import BaseIntegrationConfig

   from myproject.integrations.base import GetIntegrationManagerMixin


   class IntegrationConfig(GetIntegrationManagerMixin, BaseIntegrationConfig):
       user = models.ForeignKey(User, related_name='integration_configs')


This will give us an association between users and their integration
configurations.

Next, you may want a special subclass of
:py:class:`~djblets.integrations.forms.IntegrationConfigForm` that can work
with this new field:

.. code-block:: python

   from django import forms
   from django.contrib.auth.models import User
   from djblets.integrations.forms import (IntegrationConfigForm as
                                           BaseIntegrationConfigForm)


   class IntegrationConfigForm(BaseIntegrationConfigForm):
       model_fields = (
           BaseIntegrationConfigForm.model_fields +
           ('user',)
       )

       user = forms.ModelChoiceField(
           label='User',
           queryset=User.objects.all(),
           required=True)


This gives you a form that will contain these extra fields. Note that these
fields will, in the default template, be presented to the user. This may *not*
be what you want, depending on your use case!
