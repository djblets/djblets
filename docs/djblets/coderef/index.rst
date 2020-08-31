.. _djblets-coderef:

===========================
Module and Class References
===========================


.. _coderef-djblets:

Top-Level Modules
=================

.. autosummary::
   :toctree: python

   djblets
   djblets.deprecation


.. _coderef-djblets-auth:

Authentication
==============

.. autosummary::
   :toctree: python

   djblets.auth.forms
   djblets.auth.ratelimit
   djblets.auth.signals
   djblets.auth.util
   djblets.auth.views


.. _coderef-djblets-avatars:

Avatars
=======

.. autosummary::
   :toctree: python

   djblets.avatars.errors
   djblets.avatars.forms
   djblets.avatars.registry
   djblets.avatars.services
   djblets.avatars.services.base
   djblets.avatars.services.fallback
   djblets.avatars.services.file_upload
   djblets.avatars.services.gravatar
   djblets.avatars.services.url
   djblets.avatars.settings


.. seealso::

   :ref:`avatar-guides`


.. _coderef-djblets-cache:

Caching
=======

.. autosummary::
   :toctree: python

   djblets.cache.backend
   djblets.cache.backend_compat
   djblets.cache.context_processors
   djblets.cache.errors
   djblets.cache.forwarding_backend
   djblets.cache.serials
   djblets.cache.synchronizer


.. _coderef-djblets-conditions:

Conditions
==========

.. autosummary::
   :toctree: python

   djblets.conditions
   djblets.conditions.choices
   djblets.conditions.conditions
   djblets.conditions.errors
   djblets.conditions.operators
   djblets.conditions.values


.. _coderef-djblets-configforms:

Config Forms
============

.. autosummary::
   :toctree: python

   djblets.configforms.forms
   djblets.configforms.mixins
   djblets.configforms.pages
   djblets.configforms.registry
   djblets.configforms.views


.. _coderef-djblets-datagrids:

Datagrids
=========

.. autosummary::
   :toctree: python

   djblets.datagrid.grids
   djblets.datagrid.templatetags.datagrid


.. _coderef-djblets-db:

Database Utilities
==================

.. autosummary::
   :toctree: python

   djblets.db.backends.mysql.base
   djblets.db.fields
   djblets.db.fields.base64_field
   djblets.db.fields.counter_field
   djblets.db.fields.json_field
   djblets.db.fields.modification_timestamp_field
   djblets.db.fields.relation_counter_field
   djblets.db.managers
   djblets.db.query
   djblets.db.validators


.. _coderef-djblets-extensions:

Extensions
==========

.. autosummary::
   :toctree: python

   djblets.extensions.admin
   djblets.extensions.errors
   djblets.extensions.extension
   djblets.extensions.forms
   djblets.extensions.hooks
   djblets.extensions.loaders
   djblets.extensions.manager
   djblets.extensions.middleware
   djblets.extensions.models
   djblets.extensions.packaging
   djblets.extensions.resources
   djblets.extensions.settings
   djblets.extensions.signals
   djblets.extensions.staticfiles
   djblets.extensions.testing
   djblets.extensions.testing.testcases
   djblets.extensions.urls
   djblets.extensions.views
   djblets.extensions.templatetags.djblets_extensions


.. seealso::

   :ref:`extension-guides`


.. _coderef-djblets-features:

Feature Checks
==============

.. autosummary::
   :toctree: python

   djblets.features
   djblets.features.checkers
   djblets.features.decorators
   djblets.features.errors
   djblets.features.feature
   djblets.features.level
   djblets.features.registry
   djblets.features.testing
   djblets.features.templatetags.features


.. seealso::

   :ref:`feature-checks-guides`


.. _coderef-djblets-feedview:

Feed View for RSS
=================

.. autosummary::
   :toctree: python

   djblets.feedview.views
   djblets.feedview.templatetags.feedtags


.. _coderef-djblets-forms:

Form Utilities
==============

.. autosummary::
   :toctree: python

   djblets.forms.fields
   djblets.forms.fieldsets
   djblets.forms.forms
   djblets.forms.forms.key_value_form
   djblets.forms.widgets


.. _coderef-djblets-gravatars:

Gravatars
=========

.. autosummary::
   :toctree: python

   djblets.gravatars
   djblets.gravatars.templatetags.gravatars


.. _coderef-djblets-http:

HTTP Utilities
==============

.. autosummary::
   :toctree: python

   djblets.http.middleware


.. _coderef-djblets-integrations:

Integrations
============

.. autosummary::
   :toctree: python

   djblets.integrations.errors
   djblets.integrations.forms
   djblets.integrations.hooks
   djblets.integrations.integration
   djblets.integrations.manager
   djblets.integrations.mixins
   djblets.integrations.models
   djblets.integrations.templatetags.integrations
   djblets.integrations.urls
   djblets.integrations.views


.. seealso::

   :ref:`integration-guides`


.. _coderef-djblets-log:

Log Handlers and Viewer
=======================

.. autosummary::
   :toctree: python

   djblets.log
   djblets.log.middleware
   djblets.log.siteconfig
   djblets.log.urls
   djblets.log.views


.. _coderef-djblets-mail:

Mail Sending
============

.. autosummary::
   :toctree: python

   djblets.mail.dmarc
   djblets.mail.message
   djblets.mail.testing
   djblets.mail.utils


.. _coderef-djblets-markdown:

Markdown Utilities and Extensions
=================================

.. autosummary::
   :toctree: python

   djblets.markdown
   djblets.markdown.extensions.escape_html
   djblets.markdown.extensions.wysiwyg
   djblets.markdown.extensions.wysiwyg_email


.. _coderef-djblets-pipeline:

Django Pipeline Additions
=========================

.. autosummary::
   :toctree: python

   djblets.pipeline.compilers.es6.ES6Compiler
   djblets.pipeline.compilers.less.LessCompiler


.. _coderef-djblets-privacy:

Privacy Protection
==================

.. autosummary::
   :toctree: python

   djblets.privacy.consent
   djblets.privacy.consent.base
   djblets.privacy.consent.common
   djblets.privacy.consent.errors
   djblets.privacy.consent.forms
   djblets.privacy.consent.hooks
   djblets.privacy.consent.registry
   djblets.privacy.consent.tracker
   djblets.privacy.models
   djblets.privacy.pii
   djblets.privacy.templatetags.djblets_privacy


.. seealso::

   :ref:`privacy-guides`


.. _coderef-djblets-recaptcha:

reCAPTCHA
=========

.. autosummary::
   :toctree: python

   djblets.recaptcha.mixins
   djblets.recaptcha.siteconfig
   djblets.recaptcha.templatetags.djblets_recaptcha
   djblets.recaptcha.widgets


.. seealso::

   :ref:`recaptcha-guides`


.. _coderef-djblets-registries:

Registries
==========

.. autosummary::
   :toctree: python

   djblets.registries
   djblets.registries.errors
   djblets.registries.importer
   djblets.registries.mixins
   djblets.registries.registry
   djblets.registries.signals


.. seealso::

   :ref:`registry-guides`


.. _coderef-djblets-siteconfig:

Site Configuration
==================

.. autosummary::
   :toctree: python

   djblets.siteconfig
   djblets.siteconfig.admin
   djblets.siteconfig.context_processors
   djblets.siteconfig.django_settings
   djblets.siteconfig.forms
   djblets.siteconfig.managers
   djblets.siteconfig.middleware
   djblets.siteconfig.models
   djblets.siteconfig.signals
   djblets.siteconfig.views


.. _coderef-djblets-template:

Template Utilities
==================

.. autosummary::
   :toctree: python

   djblets.template.caches
   djblets.template.context
   djblets.template.loaders.conditional_cached
   djblets.template.loaders.namespaced_app_dirs


.. _coderef-djblets-testing:

Testing Helpers
===============

.. autosummary::
   :toctree: python

   djblets.testing.decorators
   djblets.testing.testcases
   djblets.testing.testrunners


.. _coderef-djblets-urls:

URL Utilities
=============

.. autosummary::
   :toctree: python

   djblets.urls.context_processors
   djblets.urls.decorators
   djblets.urls.patterns
   djblets.urls.resolvers
   djblets.urls.root
   djblets.urls.staticfiles


.. _coderef-djblets-utils:

Generic Utilities
=================

.. autosummary::
   :toctree: python

   djblets.util.compat.django.core.cache
   djblets.util.compat.django.core.files.locks
   djblets.util.compat.django.core.management.base
   djblets.util.compat.django.core.validators
   djblets.util.compat.django.shortcuts
   djblets.util.compat.django.template.context
   djblets.util.compat.django.template.loader
   djblets.util.compat.django.utils.functional
   djblets.util.compat.python.past
   djblets.util.contextmanagers
   djblets.util.dates
   djblets.util.decorators
   djblets.util.filesystem
   djblets.util.html
   djblets.util.http
   djblets.util.humanize
   djblets.util.json_utils
   djblets.util.properties
   djblets.util.serializers
   djblets.util.templatetags.djblets_deco
   djblets.util.templatetags.djblets_email
   djblets.util.templatetags.djblets_forms
   djblets.util.templatetags.djblets_images
   djblets.util.templatetags.djblets_js
   djblets.util.templatetags.djblets_utils
   djblets.util.views


.. _coderef-djblets-views:

View Helpers
============

.. autosummary::
   :toctree: python

   djblets.views.generic.base
   djblets.views.generic.etag


.. _coderef-djblets-webapi:

Web API
=======

.. autosummary::
   :toctree: python

   djblets.webapi.auth
   djblets.webapi.auth.backends
   djblets.webapi.auth.backends.api_tokens
   djblets.webapi.auth.backends.base
   djblets.webapi.auth.backends.basic
   djblets.webapi.auth.backends.oauth2_tokens
   djblets.webapi.auth.views
   djblets.webapi.decorators
   djblets.webapi.encoders
   djblets.webapi.errors
   djblets.webapi.fields
   djblets.webapi.managers
   djblets.webapi.models
   djblets.webapi.oauth2_scopes
   djblets.webapi.resources
   djblets.webapi.resources.base
   djblets.webapi.resources.group
   djblets.webapi.resources.registry
   djblets.webapi.resources.root
   djblets.webapi.resources.user
   djblets.webapi.resources.mixins.api_tokens
   djblets.webapi.resources.mixins.forms
   djblets.webapi.resources.mixins.oauth2_tokens
   djblets.webapi.resources.mixins.queries
   djblets.webapi.responses
   djblets.webapi.signals
   djblets.webapi.testing
   djblets.webapi.testing.decorators
   djblets.webapi.testing.testcases


.. seealso::

   :ref:`webapi-guides`
