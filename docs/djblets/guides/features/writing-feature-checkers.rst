.. _writing-feature-checkers:

========================
Writing Feature Checkers
========================

.. py:currentmodule:: djblets.features.checkers

Feature checkers are small classes that determine whether a feature should be
enabled or disabled. They do this by making a determination based on a
feature stability level and based on any arguments passed to the checker.

Any application that ties features to users or their teams, or has other more
complex needs, will have to write a feature checker.


Feature Enabled Checks
======================

When writing a feature checker, you usually will only need to implement a
single function: :py:meth:`~BaseFeatureChecker.is_feature_enabled`. This is
used to determine if a feature is enabled, based on some criteria defined by
the checker. This criteria can include some global state (such as
pre-configured settings) or can be based off keyword arguments passed to the
function.

For instance, you may want to write a feature checker that takes into account
the enabled feature IDs in a user's profile, falling back on values in
:file:`settings.py`:

.. code-block:: python

   from django.conf import settings
   from djblets.features.checkers import BaseFeatureChecker


   class MyFeatureChecker(BaseFeatureChecker):
       def is_feature_enabled(self, feature_id, user=None, **kwargs):
           if user:
               enabled_features = user.get_profile().enabled_features
           else:
               enabled_features = settings.ENABLED_FEATURES

           return enabled_features.get(feature_id, False)


You can do pretty much anything in this method, including querying a database.
It's really up to you.

It's important to note that your checker may be passed keyword arguments it
doesn't expect, and may not be passed arguments it does expect. It's important
to handle all cases, and to always return ``True`` or ``False``. It must never
raise an exception.


Minimum Levels
==============

A feature checker can also specify the minimum level for an enabled feature,
or can outright reject features based on their stability level. It does this
by overriding the :py:meth:`~BaseFeatureChecker.min_enabled_level` property.

For example, to enable all beta features based on a key in settings:

.. code-block:: python

   from django.conf import settings
   from djblets.features.checkers import BaseFeatureChecker
   from djblets.features.level import FeatureLevel


   class MyFeatureChecker(BaseFeatureChecker):
       @property
       def min_enabled_level(self):
           if settings.ENABLE_BETA_FEATURES:
               return FeatureLevel.BETA
           else:
               return FeatureLevel.STABLE


If you just want to hard-code a default for all cases, simply set this as an
attribute:

.. code-block:: python

   from djblets.features.checkers import BaseFeatureChecker
   from djblets.features.level import FeatureLevel


   class MyFeatureChecker(BaseFeatureChecker):
       min_enabled_level = FeatureLevel.BETA


If you're doing something more complex, and only ever need to do it once, you
may want to use a :py:func:`@cached_property
<django.utils.functional.cached_property>` decorator. For example, we might
want to use it for our settings-based check above, to avoid the unnecessary
setting lookup:

.. code-block:: python

   from django.utils.functional import cached_property
   from djblets.features.checkers import BaseFeatureChecker
   from djblets.features.level import FeatureLevel


   class MyFeatureChecker(BaseFeatureChecker):
       @cached_property
       def min_enabled_level(self):
           if settings.ENABLE_BETA_FEATURES:
               return FeatureLevel.BETA
           else:
               return FeatureLevel.STABLE
