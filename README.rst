Djblets
=======

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

* djblets.feedview_ -
  Inline RSS feed reader for news posts and other data

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
.. _Pipeline: http://django-pipeline.readthedocs.io/en/latest/
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


Compatibility
=============

Djblets 0.9 (release-0.9.x_) supports Python 2.6 and 2.7, and Django 1.6.

Djblets 1.0 (release-1.0.x_) supports Python 2.7 and Django 1.6.

Djblets 2.0 (release-2.0.x_) supports Python 2.7, 3.5, and 3.6, and Django
1.6, 1.8, 1.0. 1,0. and 1.11.

See the `release notes`_ for information on the latest public releases.


.. _release-0.9.x: https://github.com/djblets/djblets/tree/release-0.9.x
.. _release-1.0.x: https://github.com/djblets/djblets/tree/release-1.0.x
.. _release-2.0.x: https://github.com/djblets/djblets/tree/release-2.0.x
.. _release notes: https://www.reviewboard.org/docs/releasenotes/djblets/


Installing Djblets
==================

We provide source builds, Wheels, and Eggs for Djblets. We recommend you use
Wheels unless you have a reason to use Eggs or source builds.

To install Wheels via pip::

    $ pip install Djblets

To install Eggs via easy_install::

    $ easy_install Djblets


Getting Support
===============

We can help you with Djblets-related development over on our `Review Board
development list`_.


.. _Review Board development list:
   https://http://groups.google.com/group/reviewboard-dev


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

.. _Review Board Contributor Guide:
   https://www.reviewboard.org/docs/codebase/dev://www.notion.so/reviewboard/Review-Board-45d228fb07a0459b84fee509ac054cec


Related Projects
================

* `Review Board`_ -
  Our dedicated open source code review product for teams of all sizes.
