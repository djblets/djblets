"""Unit tests for djblets.util.properties."""

from __future__ import annotations

from typing import Optional, Union

from typing_extensions import assert_type

from djblets.testing.testcases import TestCase
from djblets.util.properties import AliasProperty, TypedProperty


class MyDeprecationWarning(DeprecationWarning):
    pass


class AliasPropertyTests(TestCase):
    """Unit tests for djblets.util.properties.AliasProperty."""

    def test_set(self) -> None:
        """Testing AliasProperty.__set__"""
        class MyObject:
            prop: AliasProperty[int, int] = AliasProperty('other_prop')
            other_prop = 100

        obj = MyObject()

        with self.assertNoWarnings():
            obj.prop = 42

        self.assertEqual(obj.other_prop, 42)

    def test_set_with_deprecated(self) -> None:
        """Testing AliasProperty.__set__ with deprecated=True"""
        class MyObject:
            prop: AliasProperty[int, int] = AliasProperty[int, int](
                'other_prop',
                deprecated=True,
                deprecation_warning=MyDeprecationWarning)
            other_prop = 100

        obj = MyObject()
        assert_type(obj.prop, int)

        expected_message = (
            'MyObject.prop is deprecated. Please set MyObject.other_prop '
            'instead.'
        )

        with self.assertWarns(MyDeprecationWarning, expected_message):
            obj.prop = 42

        self.assertEqual(obj.other_prop, 42)

    def test_set_with_convert_to_func(self) -> None:
        """Testing AliasProperty.__set__ with convert_to_func"""
        class MyObject:
            prop: AliasProperty[str, int] = AliasProperty[str, int](
                'other_prop',
                convert_to_func=str)
            other_prop = '100'

        obj = MyObject()

        with self.assertNoWarnings():
            # Avoid a mismatch in type checkers. Some would see 42 as `int`
            # and some would see `Literal[42]`.
            obj.prop = int(42)

        self.assertEqual(obj.other_prop, '42')
        self.assertEqual(obj.prop, '42')

    def test_set_with_convert_to_func_and_none(self) -> None:
        """Testing AliasProperty.__set__ with convert_to_func and value=None"""
        class MyObject:
            prop: AliasProperty[Optional[int], Optional[int]] = \
                AliasProperty[Optional[int], Optional[int]](
                    'other_prop',
                    convert_to_func=str)
            other_prop = '100'

        obj = MyObject()
        assert_type(obj.prop, Optional[int])

        with self.assertNoWarnings():
            obj.prop = None

        assert_type(obj.prop, None)
        self.assertIsNone(obj.other_prop)

    def test_get(self) -> None:
        """Testing AliasProperty.__get__"""
        class MyObject:
            prop: AliasProperty[int, int] = AliasProperty('other_prop')
            other_prop = 100

        obj = MyObject()
        assert_type(obj.prop, int)

        with self.assertNoWarnings():
            self.assertEqual(obj.prop, 100)

    def test_get_with_deprecated(self) -> None:
        """Testing AliasProperty.__get__ with deprecated=True"""
        class MyObject:
            prop: AliasProperty[int, int] = AliasProperty(
                'other_prop',
                deprecated=True,
                deprecation_warning=MyDeprecationWarning)
            other_prop = 100

        obj = MyObject()
        assert_type(obj.prop, int)

        expected_message = (
            'MyObject.prop is deprecated. Please access MyObject.other_prop '
            'instead.'
        )

        with self.assertWarns(MyDeprecationWarning, expected_message):
            self.assertEqual(obj.prop, 100)

    def test_get_with_convert_from_func(self) -> None:
        """Testing AliasProperty.__get__ with convert_from_func"""
        class MyObject:
            prop: AliasProperty[str, int] = AliasProperty[str, int](
                'other_prop',
                convert_from_func=str)
            other_prop = 100

        obj = MyObject()
        assert_type(obj.prop, str)

        with self.assertNoWarnings():
            self.assertEqual(obj.prop, '100')

    def test_get_with_convert_from_func_and_none(self) -> None:
        """Testing AliasProperty.__get__ with convert_from_func and value=None
        """
        class MyObject:
            prop: AliasProperty[Optional[str], Optional[str]] = \
                AliasProperty[Optional[str], Optional[str]](
                    'other_prop',
                    convert_to_func=str)
            other_prop = None

        obj = MyObject()
        assert_type(obj.prop, Optional[str])

        with self.assertNoWarnings():
            self.assertIsNone(obj.prop)


class TypedPropertyTests(TestCase):
    """Unit tests for djblets.util.properties.TypedProperty."""

    def test_with_valid_type(self) -> None:
        """Testing TypedProperty with valid type"""
        class MyObject:
            prop: TypedProperty[Union[int, bool],
                                Union[int, bool]] = TypedProperty((int, bool))

        obj = MyObject()
        assert_type(obj.prop, Union[int, bool])

        obj.prop = 100
        self.assertEqual(obj.prop, 100)

        obj.prop = True
        self.assertIs(obj.prop, True)

    def test_with_invalid_type(self) -> None:
        """Testing TypedProperty with invalid type"""
        class MyObject:
            prop: TypedProperty[str, str] = TypedProperty((str,))

        obj = MyObject()
        assert_type(obj.prop, str)

        expected_message = 'int (100) is not a valid type for this property.'

        with self.assertRaisesMessage(TypeError, expected_message):
            obj.prop = 100  # type: ignore

    def test_set_with_none_and_allow_none_true(self) -> None:
        """Testing TypedProperty.__set__ with None value and allow_none=True"""
        class MyObject:
            prop: TypedProperty[Optional[Union[int, bool]],
                                Optional[Union[int, bool]]] = \
                TypedProperty((int, bool), allow_none=True)

        obj = MyObject()
        assert_type(obj.prop, Optional[Union[int, bool]])

        obj.prop = None
        assert_type(obj.prop, None)
        self.assertIsNone(obj.prop)

    def test_set_with_none_and_allow_none_false(self) -> None:
        """Testing TypedProperty.__set__ with None value and allow_none=False
        """
        class MyObject:
            prop: TypedProperty[Union[int, bool],
                                Union[int, bool]] = \
                TypedProperty((int, bool), allow_none=False)

        obj = MyObject()
        assert_type(obj.prop, Union[int, bool])

        expected_message = 'None is not a valid value for this property.'

        with self.assertRaisesMessage(TypeError, expected_message):
            obj.prop = None  # type: ignore

    def test_get_with_default(self) -> None:
        """Testing TypedProperty.__get__ with default value"""
        class MyObject:
            prop: TypedProperty[Union[int, bool],
                                Union[int, bool]] = \
                TypedProperty((int, bool), default=100)

        obj = MyObject()

        assert_type(obj.prop, Union[int, bool])
        self.assertEqual(obj.prop, 100)
