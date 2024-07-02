"""Unit tests for djblets.util.datastructures.

Version Added:
    3.2
"""

from djblets.testing.testcases import TestCase
from djblets.util.datastructures import (dict_get_path_value,
                                         dict_set_path_value)


class DictGetPathValueTests(TestCase):
    """Unit tests for dict_get_path_value.

    Version Added:
        3.2
    """

    def test_with_single_dict(self):
        """Testing dict_get_path_value with single-level dictionary"""
        d = {
            'a': 1,
        }

        self.assertEqual(dict_get_path_value(d, ['a']), 1)

    def test_with_single_dict_key_not_found(self):
        """Testing dict_get_path_value with single-level dictionary and
        key not found
        """
        d = {
            'a': 1,
        }

        with self.assertRaisesMessage(KeyError, "Key ['b'] not found."):
            dict_get_path_value(d, ['b'])

    def test_with_nested_dict(self):
        """Testing dict_get_path_value with nested dictionaries"""
        d = {
            'a': {
                'b': {
                    'c': 123,
                },
            },
        }

        self.assertEqual(
            dict_get_path_value(d, ['a']),
            {
                'b': {
                    'c': 123,
                },
            })
        self.assertEqual(
            dict_get_path_value(d, ['a', 'b']),
            {
                'c': 123,
            })
        self.assertEqual(
            dict_get_path_value(d, ['a', 'b', 'c']),
            123)

    def test_with_nested_dict_not_found(self):
        """Testing dict_get_path_value with nested dictionaries and
        key not found
        """
        d = {
            'a': {
                'b': {
                    'c': 123,
                },
            },
        }

        with self.assertRaisesMessage(KeyError, "Key ['a', 'd'] not found."):
            dict_get_path_value(d, ['a', 'd'])

        with self.assertRaisesMessage(KeyError,
                                      "Key ['a', 'b', 'd'] not found."):
            dict_get_path_value(d, ['a', 'b', 'd'])

    def test_with_nested_dict_bad_type(self):
        """Testing dict_get_path_value with nested dictionaries and
        non-dict key in path
        """
        d = {
            'a': {
                'b': {
                    'c': 123,
                },
            },
        }

        message = (
            "Key ['a', 'b', 'c'] is not a dictionary (trying to resolve key "
            "['a', 'b', 'c', 'd'])."
        )

        with self.assertRaisesMessage(TypeError, message):
            dict_get_path_value(d, ['a', 'b', 'c', 'd'])

    def test_with_empty_path(self):
        """Testing dict_get_path_value with empty path"""
        with self.assertRaisesMessage(KeyError,
                                      'The key path cannot be empty.'):
            dict_get_path_value({}, [])


class DictSetPathValueTests(TestCase):
    """Unit tests for dict_set_path_value.

    Version Added:
        3.2
    """

    def test_with_single_dict(self):
        """Testing dict_set_path_value with single-level dictionary"""
        d = {}

        dict_set_path_value(d, ['a'], 1)

        self.assertEqual(d, {
            'a': 1,
        })

    def test_with_nested_dict(self):
        """Testing dict_set_path_value with nested dictionaries"""
        d = {}

        dict_set_path_value(d, ['a', 'b', 'c'], 1)

        self.assertEqual(d, {
            'a': {
                'b': {
                    'c': 1,
                },
            },
        })

        # Make sure merging doesn't break anything.
        dict_set_path_value(d, ['a', 'b', 'd'], 'test')
        dict_set_path_value(d, ['a', 'e'], True)

        self.assertEqual(d, {
            'a': {
                'b': {
                    'c': 1,
                    'd': 'test',
                },
                'e': True,
            },
        })

    def test_overrides_non_dicts(self):
        """Testing dict_set_path_value overrides non-dictionary keys"""
        d = {
            'a': 1,
        }

        dict_set_path_value(d, ['a', 'b'], 'test')

        self.assertEqual(d, {
            'a': {
                'b': 'test',
            },
        })

    def test_with_empty_path(self):
        """Testing dict_set_path_value with empty path"""
        with self.assertRaisesMessage(KeyError,
                                      'The key path cannot be empty.'):
            dict_set_path_value({}, [], 123)
