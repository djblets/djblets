.. _adding-oauth2-support:

=====================
Adding OAuth2 Support
=====================

.. py:currentmodule:: djblets.webapi


Overview
--------

The Web API utilities provided by Djblets can be augmented to add support for
authentication via OAuth2. In order to do this, there are a few steps:


Additional Requirements
-----------------------

OAuth2 support requires the `django-oauth-toolkit`_ module to be installed.
This module has only been tested with version 0.9.0.

.. _django-oauth-toolkit: https://pypi.python.org/pypi/django-oauth-toolkit/0.9.0


:file:`settings.py`
-------------------

The following settings need to be updated in :file:`settings.py` to take
advantage of OAuth2 support.

:setting:`INSTALLED_APPS`:
    Add ``'oauth2_provider'`` to this list.

:setting:`WEB_API_AUTH_BACKENDS`:
    Add
    ``''djblets.webapi.auth.backends.oauth2_tokens.OAuth2TokenAuthBackend'`` to
    this list.

    .. code-block:: python
       :caption: settings.py

       WEB_API_AUTH_BACKENDS = (
           'djblets.webapi.auth.backends.basic.WebAPIBasicAuthBackend',
           'djblets.webapi.auth.backends.oauth2_tokens.OAuth2TokenAuthBackend',
       )

:setting:`AUTHENTICATION_BACKENDS`:
    Create an authentication backend using :py:class:`~djblets.webapi.auth.backends.oauth2_tokens.OAuth2TokenBackendMixin`
    and add it to this setting:

    .. code-block:: python
       :caption: my_app/auth_backends.py

       from djblets.webapi.auth.backends.oauth2_tokens import OAuth2TokenBackendMixin
       from django.contrib.auth.backends import ModelBackend

       class EnabledOAuth2TokenBackend(OAuth2TokenBackendMixin, ModelBackend):
           """An OAuth2 token auth backend using a custom Application model."""

           def verify_request(self, request, token, user):
               return token.application.some_custom_property

    .. code-block:: python
       :caption: settings.py

       AUTHENTICATION_BACKENDS = (
           'django.contrib.auth.backends.ModelBackend',
           # ...
           'myapp.auth_backends.EnabledOAuth2TokenBackend',
       )

:setting:`WEB_API_ROOT_RESOURCE`:
    Define this to be the full import path of your root resource.

    .. code-block:: python
       :caption: settings.py

       WEB_API_ROOT_RESOURCE = 'myapp.webapi.resources.root.root_resource'

:setting:`WEB_API_SCOPE_DICT_CLASS`:
    This setting determines what class defines the OAuth2 scopes for your web
    API. By default, each resource will require :samp:`{scope_name}:{method}`
    where :samp:`{scope_name}` is defined by
    :py:attr:`ResourceOAuth2TokenMixin.scope_name
    <resources.mixins.oauth2_tokens.ResourceOAuth2TokenMixin.scope_name>` and
    :samp:`{method}` is one of ``read`` (for HTTP GET, HEAD, and OPTIONS),
    ``write`` (for HTTP PUT and POST), or ``destroy`` (for HTTP DELETE).

    Djblets provides two possible scope dictionary classes for your web API:

    :py:class:`djblets.webapi.oauth2_scopes.ExtensionEnabledWebAPIScopeDictionary`:
        For apps that use the djblets extensions framework.

    :py:class:`djblets.webapi.oauth2_scopes.WebAPIScopeDictionary`:
        For apps that do not use the djblets extensions framework.

    .. code-block:: python
       :caption: settings.py

       # If using extensions:
       WEB_API_SCOPE_DICT_CLASS = \
           'djblets.webapi.oauth2_scopes.ExtensionEnabledWebAPIScopeDictionary'

       # Otherwise:
       WEB_API_SCOPE_DICT_CLASS = \
           'djblets.webapi.oauth2_scopes.WebAPIScopeDictionary'


:setting:`OAUTH_PROVIDER`:
    This setting must, at a minimum, define the ``DEFAULT_SCOPES`` and
    ``SCOPES`` keys. The following example presumes that your root resource is
    named ``'root'`` and you are using one of the provided scope dictionaries.

    The ``SCOPES`` key should be an empty dictionary. It will be replaced at
    runtime with the proper dictionary.

    .. code-block:: python
       :caption: settings.py

       OAUTH2_PROVIDER = {
            'DEFAULT_SCOPES': 'root:read',
            'SCOPES': {},
       }


Resource Classes
----------------

Resources should all inherit from a base class that includes the provided
mixin for OAuth2 support.

.. code-block:: python

   from djblets.webapi.resources.base import WebAPIResource as \
       BaseWebAPIResource
   from djblets.webapi.resources.mixins.oauth2_tokens import \
       ResourceOAuth2TokenMixin


   class WebAPIResource(ResourceOAuth2TokenMixin, BaseWebAPIResource):
       """The base resource class.

       All resources should inherit from this.
       """


If you wish to disable access to a resource when using an OAuth2 token, you may
set the :py:attr:`~resources.mixins.oauth2_tokens.ResourceOAuth2TokenMixin.\
oauth2_token_access_allowed`
attribute to ``False``.


Enabling Web API OAuth Scopes
-----------------------------

Finally, to enable the web API scope dictionary, you must run
:py:func:`~djblets.webapi.oauth2_scopes.enable_webapi_scopes` at runtime. This
should be run when your app is starting.

If you are on Django 1.7+, you should call this function in your
``AppConfig.ready`` method:

.. code-block:: python
   :caption: my_app/apps.py

   from django.apps import AppConfig


   class WebApiAppConfig(AppConfig):
       def ready(self):
           """Enable the WebAPI scopes dictionary."""
           from djblets.webapi.oauth2_scopes import enable_webapi_scopes

           enable_oauth2_scopes()


Otherwise if you are on Django 1.6, you may call it in your root
:file:`urls.py`:

.. code-block:: python
   :caption: urls.py

   from djblets.webapi.oauth2_scopes import enable_webapi_scopes


   urlpatterns = [
       # ...
   ]

   enable_oauth2_scopes()
