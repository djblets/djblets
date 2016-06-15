.. _testing-with-features:

===========================
Testing with Feature Checks
===========================

.. py:currentmodule:: djblets.features.testing

Projects may ship a feature that is disabled by default, but should still be
properly unit tested, or may have a feature enabled that should appear
disabled for certain tests.

Djblets ships with utility functions that can help with feature-related unit
tests.


Overriding Feature Checks
=========================

A common task in a unit test will be to test a piece of code with one or more
features in a given state. There are two context manager functions that can
help with this: :py:func:`override_feature_check` and
:py:func:`override_feature_checks`.

:py:func:`override_feature_check` takes a single feature ID and an enabled
state to set. Any code using that feature within the context manager will see
the feature set to the desired state, regardless of its feature level. For
example:

.. code-block:: python

   from djblets.features.testing import override_feature_check


   with override_feature_check('my-feature-id', enabled=True):
       ...


:py:func:`override_feature_checks` does the same thing, but for multiple
feature checks at once. It takes a dictionary of feature IDs and their enabled
states. For example:

.. code-block:: python

   from djblets.features.testing import override_feature_checks


   feature_states = {
       'my-feature-id-1': True,
       'my-feature-id-2': False,
   }

   with override_feature_checks(feature_states):
       ...
