"""Unit tests for djblets.util.json_utils."""

from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.util.json_utils import (JSONPatchError,
                                     JSONPointerEndOfList,
                                     JSONPointerLookupError,
                                     JSONPointerSyntaxError,
                                     json_get_pointer_info,
                                     json_merge_patch,
                                     json_resolve_pointer)


class JSONMergePathTests(TestCase):
    """Unit tests for djblets.util.json_utils.json_merge_patch."""

    def test_with_change_dict_key_value(self):
        """Testing json_merge_patch with changing key's value in dictionary"""
        doc = {
            'a': 'b',
            'b': ['c'],
            'c': 'd',
            'd': [1, 2],
            'e': {
                'f': 1,
                'g': 2,
            },
        }

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch={
                    'a': 'c',
                    'b': 'd',
                    'c': ['e'],
                    'd': [3, 4],
                    'e': {
                        'f': 'ef',
                    },
                }
            ),
            {
                'a': 'c',
                'b': 'd',
                'c': ['e'],
                'd': [3, 4],
                'e': {
                    'f': 'ef',
                    'g': 2,
                },
            })

        self.assertEqual(
            doc,
            {
                'a': 'b',
                'b': ['c'],
                'c': 'd',
                'd': [1, 2],
                'e': {
                    'f': 1,
                    'g': 2,
                },
            })

    def test_with_add_dict_key(self):
        """Testing json_merge_patch with adding a new key to a dictionary"""
        doc = {
            'a': 'b',
        }

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch={
                    'b': 'c',
                    'c': ['d'],
                    'd': {
                        'e': 1,
                        'f': 2,
                    },
                }
            ),
            {
                'a': 'b',
                'b': 'c',
                'c': ['d'],
                'd': {
                    'e': 1,
                    'f': 2,
                },
            })

        self.assertEqual(
            doc,
            {
                'a': 'b',
            })

    def test_with_delete_dict_key(self):
        """Testing json_merge_patch with deleting a key in a dictionary"""
        doc = {
            'a': 'b',
            'b': 'c',
            'c': {
                'e': 1,
                'f': 2,
            },
            'd': None,
        }

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch={
                    'a': None,
                    'c': {
                        'e': None,
                    },
                    'e': None,
                }
            ),
            {
                'b': 'c',
                'c': {
                    'f': 2,
                },
                'd': None,
            })

        self.assertEqual(
            doc,
            {
                'a': 'b',
                'b': 'c',
                'c': {
                    'e': 1,
                    'f': 2,
                },
                'd': None,
            })

    def test_with_change_list(self):
        """Testing json_merge_patch with changing a list value"""
        doc = [1, 2, 3]

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch=[4, 5, 6],
            ),
            [4, 5, 6])

        self.assertEqual(doc, [1, 2, 3])

    def test_with_change_type(self):
        """Testing json_merge_patch with changing a value's type"""
        doc = [1, 2, 3]

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch={
                    'a': 1,
                }
            ),
            {
                'a': 1,
            })

        self.assertEqual(doc, [1, 2, 3])

    def test_with_can_write_key_func(self):
        """Testing json_merge_patch with can_write_key_func"""
        def _can_write_key(doc, patch, path):
            return path != ('a', 'b', 'c')

        doc = {
            'a': {
                'b': {
                    'c': 123,
                },
                'd': True,
            },
        }

        self.assertEqual(
            json_merge_patch(
                doc=doc,
                patch={
                    'a': {
                        'b': {
                            'c': 100,
                        },
                        'd': False,
                    },
                    'e': 'hi!',
                },
                can_write_key_func=_can_write_key),
            {
                'a': {
                    'b': {
                        'c': 123,
                    },
                    'd': False,
                },
                'e': 'hi!',
            })

        self.assertEqual(
            doc,
            {
                'a': {
                    'b': {
                        'c': 123,
                    },
                    'd': True,
                },
            })

    def test_with_can_write_key_func_with_patch_error(self):
        """Testing json_merge_patch with can_write_key_func raising
        JSONPatchError
        """
        def _can_write_key(doc, patch, path):
            if path == ('a', 'b', 'c'):
                raise JSONPatchError('Go away!')

            return True

        doc = {
            'a': {
                'b': {
                    'c': 123,
                },
                'd': True,
            },
        }

        with self.assertRaisesMessage(JSONPatchError, 'Go away!'):
            json_merge_patch(
                doc=doc,
                patch={
                    'a': {
                        'b': {
                            'c': 100,
                        },
                        'd': False,
                    },
                    'e': 'hi!',
                },
                can_write_key_func=_can_write_key)

        self.assertEqual(doc, {
            'a': {
                'b': {
                    'c': 123,
                },
                'd': True,
            },
        })


class JSONGetPointerInfoTests(TestCase):
    """Unit tests for djblets.util.json_utils.json_get_pointer_info."""

    def test_with_relative_path(self):
        """Testing json_get_pointer_info with relative path"""
        message = 'Paths must either be empty or start with a "/"'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_get_pointer_info({}, 'a/')

    def test_with_dict(self):
        """Testing json_get_pointer_info with valid dictionary path"""
        obj = {
            '': 'hi',
            'a': {
                'b': {
                    'c': 123,
                },
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, ''),
            {
                'value': obj,
                'parent': None,
                'resolved_values': [obj],
                'all_tokens': [],
                'resolved_tokens': [],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/'),
            {
                'value': 'hi',
                'parent': obj,
                'resolved_values': [obj, 'hi'],
                'all_tokens': [''],
                'resolved_tokens': [''],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/a'),
            {
                'value': obj['a'],
                'parent': obj,
                'resolved_values': [obj, obj['a']],
                'all_tokens': ['a'],
                'resolved_tokens': ['a'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/a/b'),
            {
                'value': obj['a']['b'],
                'parent': obj['a'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b']],
                'all_tokens': ['a', 'b'],
                'resolved_tokens': ['a', 'b'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c'),
            {
                'value': obj['a']['b']['c'],
                'parent': obj['a']['b'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b'],
                                    obj['a']['b']['c']],
                'all_tokens': ['a', 'b', 'c'],
                'resolved_tokens': ['a', 'b', 'c'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })

    def test_with_list_item(self):
        """Testing json_get_pointer_info with valid resulting list item"""
        obj = {
            'a': {
                'b': {
                    'c': [1, 2, 3],
                },
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c/0'),
            {
                'value': 1,
                'parent': obj['a']['b']['c'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b'],
                                    obj['a']['b']['c'],
                                    obj['a']['b']['c'][0]],
                'all_tokens': ['a', 'b', 'c', '0'],
                'resolved_tokens': ['a', 'b', 'c', '0'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c/1'),
            {
                'value': 2,
                'parent': obj['a']['b']['c'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b'],
                                    obj['a']['b']['c'],
                                    obj['a']['b']['c'][1]],
                'all_tokens': ['a', 'b', 'c', '1'],
                'resolved_tokens': ['a', 'b', 'c', '1'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })
        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c/2'),
            {
                'value': 3,
                'parent': obj['a']['b']['c'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b'],
                                    obj['a']['b']['c'],
                                    obj['a']['b']['c'][2]],
                'all_tokens': ['a', 'b', 'c', '2'],
                'resolved_tokens': ['a', 'b', 'c', '2'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })

    def test_with_list_item_end_of_list(self):
        """Testing json_get_pointer_info with valid resulting list item using
        "-" for end of list
        """
        obj = {
            'a': {
                'b': {
                    'c': [1, 2, 3],
                },
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c/-'),
            {
                'value': JSONPointerEndOfList([1, 2, 3]),
                'parent': obj['a']['b']['c'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b'],
                                    obj['a']['b']['c'],
                                    JSONPointerEndOfList([1, 2, 3])],
                'all_tokens': ['a', 'b', 'c', '-'],
                'resolved_tokens': ['a', 'b', 'c', '-'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })

    def test_with_nested_lists_dicts(self):
        """Testing json_get_pointer_info with valid path containing nested
        lists and dictionaries
        """
        obj = {
            'a': [
                1,
                {
                    'b': [2, 3, 'foo'],
                },
            ],
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/1/b/2'),
            {
                'value': 'foo',
                'parent': obj['a'][1]['b'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a'][1],
                                    obj['a'][1]['b'],
                                    obj['a'][1]['b'][2]],
                'all_tokens': ['a', '1', 'b', '2'],
                'resolved_tokens': ['a', '1', 'b', '2'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })

    def test_with_escaped(self):
        """Testing json_get_pointer_info with valid escaped paths"""
        obj = {
            '/': {
                '~': {
                    '~/~': 123,
                },
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/~1/~0/~0~1~0'),
            {
                'value': 123,
                'parent': obj['/']['~'],
                'resolved_values': [obj,
                                    obj['/'],
                                    obj['/']['~'],
                                    obj['/']['~']['~/~']],
                'all_tokens': ['/', '~', '~/~'],
                'resolved_tokens': ['/', '~', '~/~'],
                'unresolved_tokens': [],
                'lookup_error': None,
            })

    def test_with_bad_key(self):
        """Testing json_get_pointer_info with invalid path containing a bad
        key
        """
        obj = {
            'a': {
                'b': 123,
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/c'),
            {
                'value': None,
                'parent': obj['a'],
                'resolved_values': [obj,
                                    obj['a']],
                'all_tokens': ['a', 'c'],
                'resolved_tokens': ['a'],
                'unresolved_tokens': ['c'],
                'lookup_error': 'Dictionary key "c" not found in "/a"',
            })

    def test_with_bad_list_index(self):
        """Testing json_get_pointer_info with invalid path containing a bad
        list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/3'),
            {
                'value': None,
                'parent': obj['a']['b'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b']],
                'all_tokens': ['a', 'b', '3'],
                'resolved_tokens': ['a', 'b'],
                'unresolved_tokens': ['3'],
                'lookup_error': '3 is outside the list in "/a/b"',
            })

    def test_with_non_traversable_path(self):
        """Testing json_get_pointer_info with invalid path containing a
        non-traversable item
        """
        obj = {
            'a': {
                'b': 'test',
            },
        }

        self.assertEqual(
            json_get_pointer_info(obj, '/a/b/c'),
            {
                'value': None,
                'parent': obj['a']['b'],
                'resolved_values': [obj,
                                    obj['a'],
                                    obj['a']['b']],
                'all_tokens': ['a', 'b', 'c'],
                'resolved_tokens': ['a', 'b'],
                'unresolved_tokens': ['c'],
                'lookup_error': (
                    'Cannot resolve path within unsupported type '
                    '"unicode" at "/a/b"'
                ),
            })

    def test_with_negative_list_index(self):
        """Testing json_get_pointer_info with invalid path containing a negative
        list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'Negative indexes into lists are not allowed'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_get_pointer_info(obj, '/a/b/-1')

    def test_with_index_with_leading_zero(self):
        """Testing json_get_pointer_info with invalid path containing a list
        index with a leading zero
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'List index "01" must not begin with "0"'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_get_pointer_info(obj, '/a/b/01')

    def test_with_non_int_list_index(self):
        """Testing json_get_pointer_info with invalid path containing a
        non-integer list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'u\'c\' is not a valid list index in "/a/b"'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_get_pointer_info(obj, '/a/b/c')


class JSONResolvePointerTests(TestCase):
    """Unit tests for djblets.util.json_utils.json_resolve_pointer."""

    def test_with_dict(self):
        """Testing json_resolve_pointer with valid dictionary path"""
        obj = {
            '': 'hi',
            'a': {
                'b': {
                    'c': 123,
                },
            },
        }

        self.assertEqual(json_resolve_pointer(obj, ''), obj)
        self.assertEqual(json_resolve_pointer(obj, '/'), 'hi')
        self.assertEqual(json_resolve_pointer(obj, '/a'), {
            'b': {
                'c': 123,
            },
        })
        self.assertEqual(json_resolve_pointer(obj, '/a/b'), {
            'c': 123,
        })
        self.assertEqual(json_resolve_pointer(obj, '/a/b/c'), 123)

    def test_with_list_item(self):
        """Testing json_resolve_pointer with valid resulting list item"""
        obj = {
            'a': {
                'b': {
                    'c': [1, 2, 3],
                },
            },
        }

        self.assertEqual(json_resolve_pointer(obj, '/a/b/c/0'), 1)
        self.assertEqual(json_resolve_pointer(obj, '/a/b/c/1'), 2)
        self.assertEqual(json_resolve_pointer(obj, '/a/b/c/2'), 3)

    def test_with_list_item_end_of_list(self):
        """Testing json_resolve_pointer with valid resulting list item using
        "-" for end of list
        """
        obj = {
            'a': {
                'b': {
                    'c': [1, 2, 3],
                },
            },
        }

        self.assertIsInstance(json_resolve_pointer(obj, '/a/b/c/-'),
                              JSONPointerEndOfList)

    def test_with_nested_lists_dicts(self):
        """Testing json_resolve_pointer with valid path containing nested
        lists and dictionaries
        """
        obj = {
            'a': [
                1,
                {
                    'b': [2, 3, 'foo'],
                },
            ],
        }

        self.assertEqual(json_resolve_pointer(obj, '/a/1/b/2'), 'foo')

    def test_with_escaped(self):
        """Testing json_resolve_pointer with valid escaped paths"""
        obj = {
            '/': {
                '~': {
                    '~/~': 123,
                },
            },
        }

        self.assertEqual(json_resolve_pointer(obj, '/~1/~0/~0~1~0'), 123)

    def test_with_bad_key(self):
        """Testing json_resolve_pointer with invalid path containing a bad
        key
        """
        obj = {
            'a': {
                'b': 123,
            },
        }

        message = 'Dictionary key "c" not found in "/a"'

        with self.assertRaisesMessage(JSONPointerLookupError, message):
            json_resolve_pointer(obj, '/a/c')

    def test_with_bad_list_index(self):
        """Testing json_resolve_pointer with invalid path containing a bad
        list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = '3 is outside the list in "/a/b"'

        with self.assertRaisesMessage(JSONPointerLookupError, message):
            json_resolve_pointer(obj, '/a/b/3')

    def test_with_non_traversable_path(self):
        """Testing json_resolve_pointer with invalid path containing a
        non-traversable item
        """
        obj = {
            'a': {
                'b': 'test',
            },
        }

        message = \
            'Cannot resolve path within unsupported type "unicode" at "/a/b"'

        with self.assertRaisesMessage(JSONPointerLookupError, message):
            json_resolve_pointer(obj, '/a/b/c')

    def test_with_index_with_leading_zero(self):
        """Testing json_resolve_pointer with invalid path containing a negative
        list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'Negative indexes into lists are not allowed'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_resolve_pointer(obj, '/a/b/-1')

    def test_with_negative_list_index(self):
        """Testing json_resolve_pointer with invalid path containing a list
        index with a leading zero
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'List index "01" must not begin with "0"'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_resolve_pointer(obj, '/a/b/01')

    def test_with_non_int_list_index(self):
        """Testing json_resolve_pointer with invalid path containing a
        non-integer list index
        """
        obj = {
            'a': {
                'b': [1, 2],
            },
        }

        message = 'u\'c\' is not a valid list index in "/a/b"'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_resolve_pointer(obj, '/a/b/c')
