.. _djblets-coderef:

===========================
Module and Class References
===========================


Top-Level Modules
=================

.. autosummary::
   :toctree: python

   djblets


Authentication
==============

.. autosummary::
   :toctree: python

   djblets.auth.forms
   djblets.auth.ratelimit
   djblets.auth.signals
   djblets.auth.util
   djblets.auth.views


Avatars
=======

.. autosummary::
   :toctree: python

   djblets.avatars.errors
   djblets.avatars.forms
   djblets.avatars.registry
   djblets.avatars.settings
   djblets.avatars.services
   djblets.avatars.services.base
   djblets.avatars.services.file_upload
   djblets.avatars.services.gravatar
   djblets.avatars.services.url


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


Config Forms
============

.. autosummary::
   :toctree: python

   djblets.configforms.forms
   djblets.configforms.mixins
   djblets.configforms.pages
   djblets.configforms.registry
   djblets.configforms.views


Datagrids
=========

.. autosummary::
   :toctree: python

   djblets.datagrid.grids


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
   djblets.integrations.urls
   djblets.integrations.views
   djblets.integrations.templatetags.integrations


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


Feed View for RSS
=================

.. autosummary::
   :toctree: python

   djblets.feedview.views
   djblets.feedview.templatetags.feedtags


Form Utilities
==============

.. autosummary::
   :toctree: python

   djblets.forms.fields
   djblets.forms.fieldsets
   djblets.forms.forms
   djblets.forms.forms.key_value_form
   djblets.forms.widgets


Gravatars
=========

.. autosummary::
   :toctree: python

   djblets.gravatars
   djblets.gravatars.templatetags.gravatars


Log Handlers and Viewer
=======================

.. autosummary::
   :toctree: python

   djblets.log
   djblets.log.middleware
   djblets.log.siteconfig
   djblets.log.urls
   djblets.log.views


Mail Sending
============

.. autosummary::
   :toctree: python

   djblets.mail.dmarc
   djblets.mail.message
   djblets.mail.testing
   djblets.mail.utils


Markdown Utilities and Extensions
=================================

.. autosummary::
   :toctree: python

   djblets.markdown
   djblets.markdown.extensions.escape_html
   djblets.markdown.extensions.wysiwyg
   djblets.markdown.extensions.wysiwyg_email


Django Pipeline Additions
=========================

.. autosummary::
   :toctree: python

   djblets.pipeline.compilers.es6.ES6Compiler
   djblets.pipeline.compilers.less.LessCompiler


reCAPTCHA
=========

.. autosummary::
   :toctree: python

   djblets.recaptcha.mixins
   djblets.recaptcha.templatetags.djblets_recaptcha
   djblets.recaptcha.widgets


Registries
==========

.. autosummary::
   :toctree: python

   djblets.registries
   djblets.registries.errors
   djblets.registries.mixins
   djblets.registries.registry


Site Configuration
==================

.. autosummary::
   :toctree: python

   djblets.siteconfig
   djblets.siteconfig.context_processors
   djblets.siteconfig.django_settings
   djblets.siteconfig.forms
   djblets.siteconfig.managers
   djblets.siteconfig.middleware
   djblets.siteconfig.models
   djblets.siteconfig.signals
   djblets.siteconfig.views


Template Utilities
==================

.. autosummary::
   :toctree: python

   djblets.template.loaders.conditional_cached
   djblets.template.loaders.namespaced_app_dirs


Testing Helpers
===============

.. autosummary::
   :toctree: python

   djblets.testing.decorators
   djblets.testing.testcases
   djblets.testing.testrunners


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


Generic Utilities
=================

.. autosummary::
   :toctree: python

   djblets.util.contextmanagers
   djblets.util.dates
   djblets.util.decorators
   djblets.util.filesystem
   djblets.util.http
   djblets.util.humanize
   djblets.util.json_utils
   djblets.util.serializers
   djblets.util.views
   djblets.util.templatetags.djblets_deco
   djblets.util.templatetags.djblets_email
   djblets.util.templatetags.djblets_forms
   djblets.util.templatetags.djblets_images
   djblets.util.templatetags.djblets_js
   djblets.util.templatetags.djblets_utils


View Helpers
============

.. autosummary::
   :toctree: python

   djblets.views.generic.base
   djblets.views.generic.etag


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
   djblets.webapi.testing
   djblets.webapi.testing.decorators
   djblets.webapi.testing.testcases
