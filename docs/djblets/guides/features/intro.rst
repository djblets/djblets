.. _feature-checks-intro:

==============================
Introduction to Feature Checks
==============================

Feature checks are a way of allowing feature development to happen in a
codebase without exposing those features to all your users. You can define a
feature with an ID, name, summary, and a stability level (unavailable,
experimental, beta, or stable) and limit who's able to actually see and use
that feature, dynamically.

The ability to control access to a feature can be done in a variety of ways.
Features can be enabled based on their stability level, or based on a
per-feature setting, or based on custom logic defined in the application.

There are many modules out there that provide this functionality, with
specific ways to write and check those features. Djblets provides its own
variation in a way that's very small and very pluggable, with support for
existing Djblets features like
:py:class:`~djblets.siteconfig.models.SiteConfiguration`.

There are two main components in the feature check system: The features, and
the checkers.


Features
========

Applications should define a :py:class:`~djblets.features.feature.Feature`
subclass for every feature they want to control access to. These specify
a unique ID, a name and summary, and the current stability level of the
feature. They can also supply initialization or shutdown logic for that
feature.

A typical feature might look like:

.. code-block:: python

   from djblets.features import Feature


   class MyFeature(Feature):
       feature_id = 'myproject.myfeature'
       name = 'My Feature'
       summary = 'This feature does some neat things.'


   my_feature = MyFeature()


Checking Features
-----------------

Features can be checked in Python code:

.. code-block:: python

    if my_feature.is_enabled():
        ...


Or in templates:

.. code-block:: html+django

   {% if_feature_enabled "myproject.myfeature" %}
   ...
   {% else %}
   ...
   {% endif_feature_enabled %}


You can also do the inverse of this in templates:

.. code-block:: html+django

   {% if_feature_disabled "myproject.myfeature" %}
   ...
   {% else %}
   ...
   {% endif_feature_disabled %}


More specialized feature checkers, as we'll see below, may take other state
into consideration when determining if a feature is enabled. For instance, it
may want to consider a request or user. These can be provided as well:

.. code-block:: python

   if my_feature.is_enabled(request=request, user=user):
       ...


.. code-block:: html+django

   {% if_feature_enabled "myproject.myfeature" request=request user=user %}
   ...
   {% endif_feature_enabled %}


There's more you can do with a feature. See :ref:`writing-features`.

You may also want to look into
:ref:`testing with feature checks <testing-with-features>`, to help you write
comprehensive unit tests.


Feature Checkers
================

.. py:currentmodule:: djblets.features.checkers

Feature checkers are small classes that determine whether a feature should be
enabled or disabled. They do this by making a determination based on a
feature stability level and based on any arguments passed to the checker.

Unless otherwise customized by a subclass, feature checkers will determine
that beta-level features are enabled by default only if ``settings.DEBUG =
True``, and that stable-level features are always enabled by default. This
logic is contained within :py:meth:`~BaseFeatureChecker.min_enabled_level`.

If a feature isn't determined to be enabled based on its level, then
:py:meth:`~BaseFeatureChecker.is_feature_enabled` will make a final
determination. How it does this depends very much on the feature checker. It
can make a determination based on some global setting somewhere, or it may
consider keyword arguments passed to the function and make a determination
based on those.

An application can choose the feature checker to use by configuring
``settings.FEATURE_CHECKER`` to point to the absolute class path.


Built-in Checkers
-----------------

There are two built-in feature checkers:

:py:class:`SettingsFeatureChecker`:
    Determines whether a feature is enabled by checking for the feature's ID
    in a ``settings.ENABLED_FEATURES`` dictionary. For instance:

    .. code-block:: python

       ENABLED_FEATURES = {
           'my-feature': True,
       }

    If present and ``True``, the feature will be enabled. Otherwise, it will
    be disabled.

    This is the default feature checker.

:py:class:`SiteConfigFeatureChecker`:
   Determines whether a feature is enabled first by checking for the feature's
   ID in a ``enabled_features`` dictionary in
   :py:attr:`SiteConfiguration.settings
   <djblets.siteconfig.models.SiteConfiguration.settings>`, and then falling
   back on a ``settings.ENABLED_FEATURES`` dictionary (just like with
   :py:class:`SettingsFeatureChecker`.

   To use this, set the following in :file:`settings.py`:

   .. code-block:: python

      FEATURE_CHECKER = 'djblets.features.checkers.SiteConfigFeatureChecker'

You can also :ref:`write your own feature checker <writing-feature-checkers>`
if you want custom behavior, such as determining features per-user.


.. _feature-checks-registry:

Feature Registry
================

.. py:currentmodule:: djblets.features.registry

Every feature you instantiate gets added to the main :py:class:`feature
registry <FeatureRegistry>`. This registry allows you to dynamically look up,
unregister, and re-register features.


Looking Up Features
-------------------

You can fetch any previously-registered feature by calling
:py:meth:`~FeaturesRegistry.get_feature`:

.. code-block:: python

   from djblets.features import get_feature_registry


   get_feature_registry().get_feature('my-feature-id')


If the feature exists (doesn't return ``None``), then you can go ahead and
make some determinations based on that feature.


Iterating Features
------------------

You can also iterate through all the features by iterating through the
registry:

.. code-block:: python

   from djblets.features import get_feature_registry


   for feature in get_feature_registry():
       ...


Unregistering Features
----------------------

If you ever need to unregister a feature, you can do so with the
:py:meth:`~FeaturesRegistry.unregister` method:

.. code-block:: python

   from djblets.features import get_feature_registry

   from myapp.features import my_feature


   get_feature_registry().unregister(my_feature)


Registering Features
--------------------

If you need to re-register a feature that was previously unregistered, you can
do so with the :py:meth:`~FeaturesRegistry.register` method:

.. code-block:: python

   from djblets.features import get_feature_registry

   from myapp.features import my_feature


   get_feature_registry().register(my_feature)
