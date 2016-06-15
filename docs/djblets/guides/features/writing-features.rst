.. _writing-features:

================
Writing Features
================

.. py:currentmodule:: djblets.features.feature

Features are very small and easy to write. They're subclasses of
:py:class:`Feature`,  which are typically placed in a :file:`features.py` file
in the app defining the feature.

Let's start with a basic example:

.. code-block:: python

   # myapp/features.py

   from djblets.features import Feature, FeatureLevel


   class MyFeature(Feature):
       feature_id = 'myproject.myfeature'
       name = 'My Feature'
       summary = 'This feature does some neat things.'
       level = FeatureLevel.EXPERIMENTAL


   my_feature = MyFeature()


Each feature must have a unique ID. This ID is how you look up a feature
dynamically and is used when specifying which features are enabled (through a
feature checker).

Features should also have a name and a summary. These aren't used directly by
the Djblets Features code, but applications may want to use these to show a
human-readable list of possible features.

You'll also want to instantiate your feature subclass, but just once. We
recommend instantiating it in the same file in which it's defined, as a
top-level variable. At this point, the feature will be registered with the
:ref:`feature registry <feature-checks-registry>`, allowing the feature to be
used and its enable state computed.


Stability Levels
================

.. py:currentmodule:: djblets.features.level

A feature has a stability level, which indicates whether it's enabled by
default, or even whether it can be enabled at all.

The built-in stability levels are defined in :py:class:`FeatureLevel`, and
include:

:py:attr:`~FeatureLevel.UNAVAILABLE`:
   The feature is unavailable for use, and can't be enabled through a feature
   checker. Useful when shipping code that you don't want used at all yet by
   anybody else, and you just want to selectively enable in your own tree or
   in a development branch.

:py:attr:`~FeatureLevel.EXPERIMENTAL`:
   The feature is experimental and disabled by default, but can be enabled
   through the feature checker.

:py:attr:`~FeatureLevel.BETA`:
   The feature is in beta. It will be disabled by default if
   ``settings.DEBUG`` is ``False``, but can be enabled through the feature
   checker. If ``settings.DEBUG`` is ``True``, it will be enabled.

:py:attr:`~FeatureLevel.STABLE`:
   The feature is always enabled.

The meaning of these levels can be changed in the feature checker by
overriding
:py:meth:`~djblets.features.checkers.BaseFeatureChecker.min_enabled_level`.


.. py:currentmodule:: djblets.features.feature

You can set the stability level of your feature through the
:py:attr:`Feature.level` attribute:

.. code-block:: python

   from djblets.features import FeatureLevel


   class MyFeature(Feature):
       level = FeatureLevel.BETA


Feature Initialization/Shutdown
===============================

If you need to perform some logic surrounding the initialization of a feature,
such as registering signal handlers, then you can do so by defining a
:py:meth:`~Feature.initialize` method:

.. code-block:: python

   class MyFeature(Feature):
       ...

       def initialize(self):
           # Your code goes here.


Similarly, you can handle feature shutdown through a
:py:meth:`~Feature.shutdown` method. This is only ever called if the
application unregisters the feature, which not all applications will do, but
if yours does, this would be a good place to put shutdown logic.

.. code-block:: python

   class MyFeature(Feature):
       ...

       def shutdown(self):
           # Your code goes here.


Not all features are going to need these capabilities, but they're there if
you do need them.
