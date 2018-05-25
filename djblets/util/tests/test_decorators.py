"""Unit tests for djblets.util.decorators."""

from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.util.decorators import cached_property, optional_decorator


class DecoratorTests(TestCase):
    """Unit tests for djblets.util.decorators."""

    def test_cached_property(self):
        """Testing @cached_property retains attributes and docstring"""
        class MyClass(object):
            def expensive_method(self, state=[0]):
                state[0] += 1

                return state[0]

            def my_prop1(self):
                """This is my docstring."""
                return self.expensive_method()

            my_prop1.some_attr = 105
            my_prop1 = cached_property(my_prop1)

            @cached_property
            def my_prop2(self):
                """Another one!"""
                return 'foo'

        instance = MyClass()

        self.assertEqual(instance.my_prop1, 1)
        self.assertEqual(instance.my_prop1, 1)
        self.assertEqual(instance.my_prop2, 'foo')

        prop1_instance = instance.__class__.__dict__['my_prop1']
        self.assertEqual(prop1_instance.__name__, 'my_prop1')
        self.assertEqual(prop1_instance.__doc__, 'This is my docstring.')
        self.assertEqual(getattr(prop1_instance, 'some_attr'), 105)

        prop2_instance = instance.__class__.__dict__['my_prop2']
        self.assertEqual(prop2_instance.__name__, 'my_prop2')
        self.assertEqual(prop2_instance.__doc__, 'Another one!')
        self.assertFalse(hasattr(prop2_instance, 'some_attr'))

    def test_optional_decorator(self):
        """Testing @optional_decorator"""
        def predicate(x):
            return x != 42

        def decorator(f):
            def decorated(x):
                return f(x) + 1

            return decorated

        @optional_decorator(decorator, predicate)
        def f(x):
            return x

        self.assertEqual(f(0), 1)
        self.assertEqual(f(1), 2)
        self.assertEqual(f(42), 42)
