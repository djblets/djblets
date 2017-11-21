.. _testing-extensions:

==================
Testing Extensions
==================

.. currentmodule:: djblets.extensions.testing.testcases
.. versionadded:: 0.8.27
.. versionadded:: 0.9.4


Overview
========

To ensure that your extension works as expected and continues to work in the
future, it's recommended that your extension come with some unit tests.

Starting in Djblets 1.0, we make it much easier to write unit tests for your
extension. Your extension will need to ship with two things: A set of test
cases, and a test runner.


Writing Test Cases
==================

Extension test cases can use a mixin, :py:class:`ExtensionTestCaseMixin`, to
set up and enable an extension instance to test against. This takes an
extension class as a class attribute, and optionally allows custom metadata
and a package name to be set. The individual tests can then make use of an
extension instance.

For example:

.. code-block:: python

    from django.test import TestCase
    from djblets.extensions.testing import ExtensionTestCaseMixin

    from my_extension.extension import MyExtension


    class MyExtensionTests(ExtensionTestCaseMixin, TestCase):
        extension_class = MyExtension

        def test_something(self):
            self.assertEqual(self.extension.some_call(), 'some value')


Extensions may want to create a base class that utilizes the mixins and sets
the :py:attr:`~ExtensionTestCaseMixin.extension_class` attribute, and subclass
that for all individual test suites. For example:

.. code-block:: python

    from django.test import TestCase
    from djblets.extensions.testing import ExtensionTestCaseMixin

    from my_extension.extension import MyExtension


    class MyExtensionTestCase(ExtensionTestCaseMixin, TestCase):
        extension_class = MyExtension


    class MyExtensionTests(MyExtensionTestCase):
        def test_something(self):
            self.assertEqual(self.extension.some_call(), 'some value')


.. note::

   If you're writing extensions for `Review Board`_, you'll want to use
   :py:class:`reviewboard.testing.testcase.TestCase` instead of
   :py:class:`django.test.TestCase` for the base class.


.. _Review Board: https://www.reviewboard.org/


Writing a Test Runner
=====================

Your extension will also need a test runner. Djblets offers a handy one
built-in that's ready for extensions to use:
:py:class:`djblets.testing.testrunners.TestRunner`.

To make use of this, you'll want to create a subclass with some state, set up
your Django environment for your project, and invoke the test runner.

.. note::

   If you're developing extensions for Review Board, you don't need to do this
   at all. Instead, you'll use the :command:`rbext test` command to run your
   tests.

A test runner script might look like:

.. code-block:: python

    #!/usr/bin/env python

    import os
    import sys

    os.environ['DJANGO_SETTINGS_MODULE'] = 'myapp.settings'

    from djblets.testing.testrunners import TestRunner

    test_runner = TestRunner(test_packages=['my_extension'])

    # Run the test suite, passing any specific test names to run that the
    # user may have specified on the command line.
    failures = test_runner.run_tests(sys.argv[1:])

    if failures:
        sys.exit(1)

A couple things to note:

1. You'll need to adjust this to point to the correct Django settings module
   for the project that uses the extension, and you also may need to set up
   other state for the environment (for example, the project might require
   a :file:`settings_local.py` or similar that contains database settings or
   other such data).

2. The project you're developing extensions for may have its own specialized
   test runner to use that sets up additional stuff for you. Follow the
   project's documentation.
