Djblets: Your Django Power Tools
================================

**Project:** |license-badge| |reviewed-badge|

**Latest release:** |latest-version-badge| |latest-pyvers-badge|
|latest-django-badge|

Djblets is a large collection of general and special-purpose building blocks
designed to help with the development of web applications written using
Django_ and Python.

The following modules are available. These contain classes, functions,
template tags, templates, etc. that can be used by your own codebase.

* djblets.auth_ -
  Authentication-related utilities for registration, login rate limiting, and
  other auth-related uses

* djblets.avatars_ -
  Avatar rendering with flexible backends (supporting Gravatars, custom URLs,
  file uploads, or custom options)

* djblets.cache_ -
  Helpers for working with client-side and server-side caching needs

* djblets.conditions_ -
  User-defined condition rules under which actions should be performed

* djblets.configforms_ -
  Category-based, multi-form configuration pages

* djblets.datagrid_ -
  Customizable grids for displaying information, with custom columns

* djblets.db_ -
  Specialized fields, validation, and query operations for databases

* djblets.extensions_ -
  Extension framework, allowing third-party developers to extend your product
  or service

* djblets.features_ -
  Feature flags for enabling/disabling functionality based on any criteria

* djblets.forms_ -
  Specialized fields and widgets, enhanced form rendering, and
  dictionary-backed form data

* djblets.gravatars_ -
  Low-level functions and template tags for injecting Gravatars_ into pages

* djblets.http_ -
  Utilities for working with HTTP requests and responses.

* djblets.integrations_ -
  Framework for integrating with third-party services and offering unlimited
  numbers of user-defined configurations

* djblets.log_ -
  Enhanced logging capabilities and log viewing

* djblets.mail_ -
  Enhanced Mail sending with DMARC checks and send-on-behalf-of-user
  functionality

* djblets.markdown_ -
  Markdown rendering for pages and e-mails, with WYSIWYG editing/rendering
  support

* djblets.pipeline_ -
  Pipeline_ compilers for ES6 JavaScript and optimized LessCSS support

* djblets.privacy_ -
  Privacy-by-design support, allowing consent to be requested and tracked
  and personal information redacted

* djblets.recaptcha_ -
  Mixins and form widgets for reCAPTCHA_ integration

* djblets.registries_ -
  Base support for defining in-code registries, which tracks and allows lookup
  of custom-registered objects

* djblets.secrets_ -
  Uilities and infrastructure for encryption/decryption and token generation.

* djblets.siteconfig_ -
  In-database site configuration and settings, with Django settings mappings

* djblets.template_ -
  Loaders for intelligent template caching and utilities for working with
  template caches and state

* djblets.testing_ -
  Utilities for enhancing unit tests and defining smarter test runners

* djblets.urls_ -
  Flexible root-level URL handlers, dynamic URL patterns that can be changed
  at runtime, and more

* djblets.util_ -
  An assortment of misc. utility functions and template tags

* djblets.views_ -
  Class-based View mixins for controlling caching and more complex dispatch
  behavior

* djblets.webapi_ -
  Foundation for building fully-featured, consisent, maintainable REST APIs

We built and maintain Djblets as part of the `Review Board`_ code review
product and Splat_ bug tracker at Beanbag_.

See the documentation_ for guides and code references for working with
Djblets.


.. _Beanbag: https://www.beanbaginc.com/
.. _Django: https://www.djangoproject.com/
.. _GDPR: https://www.eugdpr.org/
.. _Gravatars: https://gravatars.com/
.. _Pipeline: https://django-pipeline.readthedocs.io/en/latest/
.. _reCAPTCHA: https://www.google.com/recaptcha/
.. _Review Board: https://www.reviewboard.org/
.. _Splat: https://www.hellosplat.com/
.. _documentation: https://www.reviewboard.org/docs/djblets/latest/

.. _djblets.auth:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-auth
.. _djblets.avatars:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-avatars
.. _djblets.cache:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-cache
.. _djblets.conditions:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-conditions
.. _djblets.configforms:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-configforms
.. _djblets.datagrid:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-datagrid
.. _djblets.db:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-db
.. _djblets.extensions:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-extensions
.. _djblets.features:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-features
.. _djblets.feedview:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-feedview
.. _djblets.forms:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-forms
.. _djblets.gravatars:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-gravatars
.. _djblets.http:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-http
.. _djblets.integrations:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-integrations
.. _djblets.log:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-log
.. _djblets.mail:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-mail
.. _djblets.markdown:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-markdown
.. _djblets.pipeline:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-pipeline
.. _djblets.privacy:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-privacy
.. _djblets.recaptcha:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-recaptcha
.. _djblets.registries:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-registries
.. _djblets.secrets:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-secrets
.. _djblets.siteconfig:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-siteconfig
.. _djblets.template:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-template
.. _djblets.testing:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-testing
.. _djblets.urls:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-urls
.. _djblets.util:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-util
.. _djblets.views:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-views
.. _djblets.webapi:
   https://www.reviewboard.org/docs/djblets/latest/coderef/#coderef-djblets-webapi

.. |latest-django-badge| image:: https://img.shields.io/pypi/frameworkversions/django/Djblets
   :target: https://www.djangoproject.com
.. |latest-pyvers-badge| image:: https://img.shields.io/pypi/pyversions/Djblets
   :target: https://pypi.org/project/Djblets
.. |latest-version-badge| image:: https://img.shields.io/pypi/v/Djblets
   :target: https://pypi.org/project/Djblets
.. |license-badge| image:: https://img.shields.io/badge/license-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
.. |reviewed-badge| image:: https://img.shields.io/badge/Review%20Board-d0e6ff?label=reviewed%20with
   :target: https://www.reviewboard.org


Compatibility
=============

Djblets 5.x (release-5.x_) supports Python 3.8-3.12 and Django 4.2.

Djblets 4.x (release-4.x_) supports Python 3.8-3.12 and Django 3.2.

Djblets 3.x (release-3.x_) supports Python 3.7-3.11 and Django 3.2.

Djblets 2.x (release-2.x_) supports Python 2.7, 3.5, and 3.6, and Django
1.6, 1.8, 1.0. 1,0. and 1.11.

Djblets 1.x (release-1.0.x_) supports Python 2.7 and Django 1.6.

Djblets 0.9 (release-0.9.x_) supports Python 2.6 and 2.7, and Django 1.6.

See the `release notes`_ for information on the latest public releases.


.. _release-0.9.x: https://github.com/djblets/djblets/tree/release-0.9.x
.. _release-1.0.x: https://github.com/djblets/djblets/tree/release-1.0.x
.. _release-2.x: https://github.com/djblets/djblets/tree/release-2.x
.. _release-3.x: https://github.com/djblets/djblets/tree/release-3.x
.. _release-4.x: https://github.com/djblets/djblets/tree/release-4.x
.. _release-5.x: https://github.com/djblets/djblets/tree/release-5.x
.. _release notes: https://www.reviewboard.org/docs/releasenotes/djblets/


Installing Djblets
==================

We provide source builds and Python Wheels for Djblets.

We recommend you use Wheels unless you have a reason to use source builds
(which requires a proper build setup for static media).

To install Wheels via pip::

    $ pip install Djblets


Getting Support
===============

We can help you with Djblets-related development over on our `Review Board
development list`_.

We also provide more `dedicated, private support
<https://www.reviewboard.org/support/>`_ for your organization through a
support contract, offering:

* Same-day responses (generally within a few hours, if not sooner)
* Confidential communications
* Installation/upgrade assistance
* Emergency database repair
* Video/chat meetings (by appointment)
* Priority fixes for urgent bugs
* Backports of urgent fixes to older releases (when possible)

Support contracts fund the development of Djblets, Review Board, and our other
open source projects.


.. _Review Board development list:
   https://groups.google.com/group/reviewboard-dev


Reporting Bugs
==============

Hit a bug? Let us know by
`filing a bug report <https://www.reviewboard.org/bugs/new/>`_.

You can also look through the
`existing bug reports <https://www.reviewboard.org/bugs/>`_ to see if anyone
else has already filed the bug.


Contributing
============

Are you a developer? Do you want to integrate Djblets into your project and
contribute back? Great! Let's help get you started.

First off, we have a few handy guides:

* `Review Board Contributor Guide`_ -
  This generally applies to Djblets as well.

We accept patches on `reviews.reviewboard.org
<https://reviews.reviewboard.org/>`_. (Please note that we *do not* accept pull
requests.)

To post a change for review:

1. Download RBTools:

   .. code-block:: console

      $ pip install rbtools

2. Create a branch in your Git clone and make your changes.

3. Post the change for review:

   .. code-block:: console

      $ rbt post

   To update your change:

   .. code-block:: console

      $ rbt post -u


.. _Review Board Contributor Guide:
   https://www.notion.so/reviewboard/Review-Board-45d228fb07a0459b84fee509ac054cec


Our Other Projects
==================

* `Review Board`_ -
  Our dedicated open source code review product for teams of all sizes.

* `Housekeeping <https://github.com/beanbaginc/housekeeping>`_ -
  Deprecation management for Python modules, classes, functions, and
  attributes.

* `kgb <https://github.com/beanbaginc/kgb>`_ -
  A powerful function spy implementation to help write Python unit tests.

* `Registries <https://github.com/beanbaginc/python-registries>`_ -
  A flexible, typed implementation of the Registry Pattern for more
  maintainable and extensible codebases.

* `Typelets <https://github.com/beanbaginc/python-typelets>`_ -
  Type hints and utility objects for Python and Django projects.

You can see more on `github.com/beanbaginc <https://github.com/beanbaginc>`_
and `github.com/reviewboard <https://github.com/reviewboard>`_.
