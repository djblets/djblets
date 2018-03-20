"""Unit tests for djblets.util.json_utils."""

from __future__ import unicode_literals

from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.util.json_utils import (JSONPatchError,
                                     JSONPatchPathError,
                                     JSONPatchReadAccessError,
                                     JSONPatchTestError,
                                     JSONPatchWriteAccessError,
                                     JSONPointerEndOfList,
                                     JSONPointerLookupError,
                                     JSONPointerSyntaxError,
                                     json_get_pointer_info,
                                     json_merge_patch,
                                     json_patch,
                                     json_resolve_pointer)


class JSONMergePatchTests(TestCase):
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

    def test_with_can_write_key_func_not_callable(self):
        """Testing json_merge_patch with can_write_key_func not callable"""
        message = 'can_write_key_func must be callable'

        with self.assertRaisesMessage(ValueError, message):
            json_merge_patch(doc={},
                             patch={},
                             can_write_key_func=123)

    def test_with_can_write_key_func_with_patch_error(self):
        """Testing json_merge_patch with can_write_key_func raising
        JSONPatchError
        """
        def _can_write_key(doc, patch, path):
            if path == ('a', 'b', 'c'):
                raise JSONPatchError('Go away!',
                                     doc=doc,
                                     patch=patch)

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


class JSONPatchTests(TestCase):
    """Unit tests for djblets.util.json_utils.json_patch."""

    def test_with_patch_not_list(self):
        """Testing json_patch with patch not a list"""
        message = 'The patch must be a list of operations to perform'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc={}, patch={})

        e = cm.exception
        self.assertEqual(e.doc, {})
        self.assertEqual(e.patch, {})
        self.assertIsNone(e.patch_entry_index)

    def test_with_patch_entry_not_dict(self):
        """Testing json_patch with patch entry not a dictionary"""
        message = 'Patch entry 0 must be a dictionary instead of list'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc={}, patch=[[]])

        e = cm.exception
        self.assertEqual(e.doc, {})
        self.assertEqual(e.patch, [[]])
        self.assertEqual(e.patch_entry_index, 0)

    def test_with_patch_entry_missing_op(self):
        """Testing json_patch with patch entry missing op"""
        message = 'Missing key "op" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc={}, patch=[{}])

        e = cm.exception
        self.assertEqual(e.doc, {})
        self.assertEqual(e.patch, [{}])
        self.assertEqual(e.patch_entry_index, 0)

    def test_with_dict_and_empty_patch(self):
        """Testing json_patch with dictionary object and empty patch"""
        doc = {
            'foo': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[]),
            {
                'foo': 1,
            })
        self.assertEqual(
            doc,
            {
                'foo': 1,
            })

    def test_with_list_and_empty_patch(self):
        """Testing json_patch with list object and empty patch"""
        doc = ['foo']

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[]),
            ['foo'])

    def test_add_replacing_field(self):
        """Testing json_patch with add op replacing existing field"""
        doc = {
            'foo': None,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/foo',
                    'value': 1,
                }]),
            {
                'foo': 1,
            })
        self.assertEqual(
            doc,
            {
                'foo': None,
            })

    def test_add_to_top_level_dict(self):
        """Testing json_patch with add op in top-level dictionary"""
        doc = {}

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/foo',
                    'value': 'bar',
                }]),
            {
                'foo': 'bar',
            })
        self.assertEqual(doc, {})

    def test_add_to_top_level_array(self):
        """Testing json_patch with add op in top-level array"""
        doc = []

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/0',
                    'value': 'foo',
                }]),
            ['foo'])
        self.assertEqual(doc, [])

    def test_add_with_append_to_top_level_array(self):
        """Testing json_patch with add op with appending to top-level array"""
        doc = ['a', 'b']

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/-',
                    'value': 'c',
                }]),
            ['a', 'b', 'c'])
        self.assertEqual(doc, ['a', 'b'])

    def test_add_with_insert_to_top_level_array(self):
        """Testing json_patch with add op with inserting into top-level array
        """
        doc = ['a', 'b']

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/1',
                    'value': 'c',
                }]),
            ['a', 'c', 'b'])
        self.assertEqual(doc, ['a', 'b'])

    def test_add_with_empty_key_on_top_level(self):
        """Testing json_patch with add op with top level and "/" path
        (signifying empty key)
        """
        doc = {}

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/',
                    'value': 1,
                }]),
            {
                '': 1,
            })
        self.assertEqual(doc, {})

    def test_add_with_empty_key_on_child(self):
        """Testing json_patch with add op with child dictionary and "/" path
        (signifying empty key)
        """
        doc = {
            'foo': {},
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/foo/',
                    'value': 1,
                }]),
            {
                'foo': {
                    '': 1,
                },
            })
        self.assertEqual(doc, {
            'foo': {},
        })

    def test_add_with_complex_path(self):
        """Testing json_patch with add op with complex path"""
        doc = {
            'a': 1,
            'b': [{
                'c': 2,
            }],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/b/0/d',
                    'value': 100,
                }]),
            {
                'a': 1,
                'b': [{
                    'c': 2,
                    'd': 100,
                }],
            })
        self.assertEqual(doc, {
            'a': 1,
            'b': [{
                'c': 2,
            }],
        })

    def test_add_with_dict_and_numeric_key(self):
        """Testing json_patch with add op with dictionary and numeric key"""
        doc = {
            'foo': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/0',
                    'value': 2,
                }]),
            {
                'foo': 1,
                '0': 2,
            })
        self.assertEqual(doc, {
            'foo': 1,
        })

    def test_add_with_array_and_index_0(self):
        """Testing json_patch with add op with array and inserting at index 0
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/a/0',
                    'value': 100,
                }]),
            {
                'a': [100, 1, 2, 3],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_add_with_array_and_last_index_plus_1(self):
        """Testing json_patch with add op with array and inserting at last
        index + 1
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/a/3',
                    'value': 100,
                }]),
            {
                'a': [1, 2, 3, 100],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_add_with_can_write_key_func_and_allowed(self):
        """Testing json_patch with add op and can_write_key_func and key
        allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'add',
                    'path': '/a/c',
                    'value': 2,
                }],
                can_write_key_func=_can_write_key),
            {
                'a': {
                    'b': 1,
                    'c': 2,
                },
            })

    def test_add_with_can_write_key_func_and_not_allowed(self):
        """Testing json_patch with add op and can_write_key_func and key
        not allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'b')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'add',
            'path': '/a/c',
            'value': 2,
        }]

        message = 'Cannot write to path "/a/c" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchWriteAccessError,
                                      message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_write_key_func=_can_write_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/c')

    def test_add_with_array_and_index_out_of_bounds(self):
        """Testing json_patch with add op with array and index out of bounds"""
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'add',
            'path': '/a/4',
            'value': 100,
        }]

        message = 'Cannot insert into index 4 in path "/a/4" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/4')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_add_with_array_and_negative_index(self):
        """Testing json_patch with add op with array and negative index"""
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'add',
            'path': '/a/-1',
            'value': 100,
        }]

        message = (
            'Syntax error in path "/a/-1" for patch entry 0: Negative indexes '
            'into lists are not allowed'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/-1')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_add_with_array_and_key(self):
        """Testing json_patch with add op with array and attempting to insert
        at key
        """
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'add',
            'path': '/a/bad',
            'value': 100,
        }]

        message = (
            'Syntax error in path "/a/bad" for patch entry 0: %r is not a '
            'valid list index in "/a"'
            % 'bad'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/bad')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_add_with_missing_path(self):
        """Testing json_patch with add op and missing path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'add',
            'value': 1,
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_add_with_missing_value(self):
        """Testing json_patch with add op and missing value"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'add',
            'path': '/a',
        }]

        message = 'Missing key "value" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_add_with_bad_path(self):
        """Testing json_patch with add op and bad path"""
        doc = {
            'a': 1,
        }

        patch = [{
            'op': 'add',
            'path': '/b/c',
            'value': 100,
        }]

        message = (
            'Invalid path "/b/c" for patch entry 0: Dictionary key "b" not '
            'found in "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b/c')

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_add_with_invalid_path_syntax(self):
        """Testing json_patch with add op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'add',
            'path': 'b',
            'value': 100,
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must either '
            'be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_remove_with_dict_key(self):
        """Testing json_patch with remove op with dictionary key"""
        doc = {
            'a': 1,
            'b': 2,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a',
                }]),
            {
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': 1,
            'b': 2,
        })

    def test_remove_with_array_index_0(self):
        """Testing json_patch with remove op with array index 0"""
        doc = {
            'a': [1, 2, 3],
            'b': 2,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a/0',
                }]),
            {
                'a': [2, 3],
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 2,
        })

    def test_remove_with_array_index_middle(self):
        """Testing json_patch with remove op with array index (middle of array)
        """
        doc = {
            'a': [1, 2, 3],
            'b': 2,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a/1',
                }]),
            {
                'a': [1, 3],
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 2,
        })

    def test_remove_with_array_index_last(self):
        """Testing json_patch with remove op with array index (last in array)
        """
        doc = {
            'a': [1, 2, 3],
            'b': 2,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a/2',
                }]),
            {
                'a': [1, 2],
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 2,
        })

    def test_remove_with_array_index_end(self):
        """Testing json_patch with remove op with array index `-` (end of
        array)
        """
        doc = {
            'a': [1, 2, 3],
            'b': 2,
        }
        patch = [{
            'op': 'remove',
            'path': '/a/-',
        }]

        message = (
            'Cannot perform operation "remove" on end of list at "/a/-" for '
            'patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/-')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 2,
        })

    def test_remove_with_complex_path(self):
        """Testing json_patch with remove op with complex path"""
        doc = {
            'a': [{
                'b': 1,
                'c': 2,
            }],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a/0/b'
                }]),
            {
                'a': [{
                    'c': 2,
                }],
            })
        self.assertEqual(doc, {
            'a': [{
                'b': 1,
                'c': 2,
            }],
        })

    def test_remove_with_repeated_removes(self):
        """Testing json_patch with remove op multiple times with different
        paths
        """
        doc = [1, 2, 3, 4]

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[
                    {
                        'op': 'remove',
                        'path': '/1',
                    },
                    {
                        'op': 'remove',
                        'path': '/2',
                    },
                ]),
            [1, 3])
        self.assertEqual(doc, [1, 2, 3, 4])

    def test_remove_with_can_write_key_func_and_allowed(self):
        """Testing json_patch with remove op and can_write_key_func and key
        allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'b')

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'remove',
                    'path': '/a/b',
                }],
                can_write_key_func=_can_write_key),
            {
                'a': {},
            })

    def test_remove_with_can_write_key_func_and_not_allowed(self):
        """Testing json_patch with remove op and can_write_key_func and key
        not allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'remove',
            'path': '/a/b',
        }]

        message = 'Cannot write to path "/a/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchWriteAccessError,
                                      message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_write_key_func=_can_write_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b')

    def test_remove_with_missing_path(self):
        """Testing json_patch with remove op and missing path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'remove',
            'value': 1,
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_remove_with_bad_path(self):
        """Testing json_patch with remove op and bad path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'remove',
            'path': '/b',
        }]

        message = (
            'Invalid path "/b" for patch entry 0: Dictionary key "b" not '
            'found in "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_remove_with_invalid_path_syntax(self):
        """Testing json_patch with remove op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'remove',
            'path': 'b',
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must either '
            'be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_remove_with_array_and_index_out_of_bounds(self):
        """Testing json_patch with remove op with array and index out of bounds
        """
        doc = {
            'a': [1, 2],
        }
        patch = [{
            'op': 'remove',
            'path': '/a/3',
        }]

        message = (
            'Invalid path "/a/3" for patch entry 0: 3 is outside the list in '
            '"/a"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/3')

        self.assertEqual(doc, {
            'a': [1, 2],
        })

    def test_replace_top_level_dict_with_array(self):
        """Testing json_patch with replace op replacing top-level dictionary
        with an array
        """
        doc = {}

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '',
                    'value': [],
                }]),
            [])
        self.assertEqual(doc, {})

    def test_replace_top_level_array_with_dict(self):
        """Testing json_patch with replace op replacing top-level array with
        a dictionary
        """
        doc = []

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '',
                    'value': {},
                }]),
            {})
        self.assertEqual(doc, [])

    def test_replace_with_dict_key(self):
        """Testing json_patch with replace op replacing key in dictionary"""
        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '/a/b',
                    'value': 2,
                }]),
            {
                'a': {
                    'b': 2,
                },
            })
        self.assertEqual(doc, {
            'a': {
                'b': 1,
            },
        })

    def test_replace_with_array_index_0(self):
        """Testing json_patch with replace op with array index 0"""
        doc = {
            'a': {
                'b': [1, 2, 3],
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '/a/b/0',
                    'value': 100,
                }]),
            {
                'a': {
                    'b': [100, 2, 3],
                },
            })
        self.assertEqual(doc, {
            'a': {
                'b': [1, 2, 3],
            },
        })

    def test_replace_with_array_index_middle(self):
        """Testing json_patch with replace op with array index (middle of
        array)
        """
        doc = {
            'a': {
                'b': [1, 2, 3],
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '/a/b/1',
                    'value': 100,
                }]),
            {
                'a': {
                    'b': [1, 100, 3],
                },
            })
        self.assertEqual(doc, {
            'a': {
                'b': [1, 2, 3],
            },
        })

    def test_replace_with_array_index_last(self):
        """Testing json_patch with replace op with array index (last in array)
        """
        doc = {
            'a': {
                'b': [1, 2, 3],
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '/a/b/2',
                    'value': 100,
                }]),
            {
                'a': {
                    'b': [1, 2, 100],
                },
            })
        self.assertEqual(doc, {
            'a': {
                'b': [1, 2, 3],
            },
        })

    def test_replace_with_array_index_end(self):
        """Testing json_patch with replace op with array index (end of array)
        """
        doc = {
            'a': {
                'b': [1, 2, 3],
            },
        }
        patch = [{
            'op': 'replace',
            'path': '/a/b/-',
            'value': 100,
        }]

        message = (
            'Cannot perform operation "replace" on end of list at "/a/b/-" '
            'for patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b/-')

        self.assertEqual(doc, {
            'a': {
                'b': [1, 2, 3],
            },
        })

    def test_replace_with_can_write_key_func_and_allowed(self):
        """Testing json_patch with replace op and can_write_key_func and key
        allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'b')

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'replace',
                    'path': '/a/b',
                    'value': 100,
                }],
                can_write_key_func=_can_write_key),
            {
                'a': {
                    'b': 100,
                },
            })

    def test_replace_with_can_write_key_func_and_not_allowed(self):
        """Testing json_patch with replace op and can_write_key_func and key
        not allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'replace',
            'path': '/a/b',
            'value': 100,
        }]

        message = 'Cannot write to path "/a/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchWriteAccessError,
                                      message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_write_key_func=_can_write_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b')

    def test_replace_with_missing_path(self):
        """Testing json_patch with replace op and missing path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'replace',
            'value': 1,
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_replace_with_bad_path(self):
        """Testing json_patch with replace op and bad path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'replace',
            'path': '/b',
            'value': 100,
        }]

        message = \
            'Cannot remove non-existent key "b" in path "/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_replace_with_invalid_path_syntax(self):
        """Testing json_patch with replace op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'replace',
            'path': 'b',
            'value': 100,
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must either '
            'be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_copy_with_dict_key(self):
        """Testing json_patch with copy op and dictionary key"""
        doc = {
            'a': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a',
                    'path': '/b'
                }]),
            {
                'a': 1,
                'b': 1,
            })
        self.assertEqual(doc, {
            'a': 1,
        })

    def test_copy_with_array_index(self):
        """Testing json_patch with copy op and array index"""
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a/1',
                    'path': '/a/0'
                }]),
            {
                'a': [2, 1, 2, 3],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_copy_with_array_index_end(self):
        """Testing json_patch with copy op and array index `-` (end of array)
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a/1',
                    'path': '/a/-'
                }]),
            {
                'a': [1, 2, 3, 2],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_copy_with_from_array_index_end(self):
        """Testing json_patch with copy op and "from" array index `-` (end of
        array)
        """
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'copy',
            'from': '/a/-',
            'path': '/a/0'
        }]

        message = (
            'Cannot perform operation "copy" from end of list at "/a/-" for '
            'patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/-')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_copy_with_array_index_to_dict_key(self):
        """Testing json_patch with copy op and array index copied to dictionary
        key
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a/1',
                    'path': '/b'
                }]),
            {
                'a': [1, 2, 3],
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_copy_with_dict_key_to_array_index(self):
        """Testing json_patch with copy op and dictionary key copied to array
        index
        """
        doc = {
            'a': [1, 2, 3],
            'b': 100,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/b',
                    'path': '/a/1'
                }]),
            {
                'a': [1, 100, 2, 3],
                'b': 100,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 100,
        })

    def test_copy_with_same_paths(self):
        """Testing json_patch with copy op and same source and destination
        paths
        """
        doc = {
            'a': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a',
                    'path': '/a'
                }]),
            {
                'a': 1,
            })
        self.assertEqual(doc, {
            'a': 1,
        })

    def test_copy_with_can_write_key_func_and_allowed(self):
        """Testing json_patch with copy op and can_write_key_func and key
        allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path == ('b',)

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a/b',
                    'path': '/b',
                }],
                can_write_key_func=_can_write_key),
            {
                'a': {
                    'b': 1,
                },
                'b': 1,
            })

    def test_copy_with_can_write_key_func_and_not_allowed(self):
        """Testing json_patch with copy op and can_write_key_func and key
        not allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path in ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'copy',
            'from': '/a/b',
            'path': '/b',
        }]

        message = 'Cannot write to path "/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchWriteAccessError,
                                      message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_write_key_func=_can_write_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

    def test_copy_with_can_read_key_func_and_allowed(self):
        """Testing json_patch with copy op and can_read_key_func and key
        allowed
        """
        def _can_read_key(doc, patch_entry, path):
            return path in (('a', 'b'), ('b',))

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'copy',
                    'from': '/a/b',
                    'path': '/b',
                }],
                can_read_key_func=_can_read_key),
            {
                'a': {
                    'b': 1,
                },
                'b': 1,
            })

    def test_copy_with_can_read_key_func_and_not_allowed(self):
        """Testing json_patch with copy op and can_read_key_func and key
        not allowed
        """
        def _can_read_key(doc, patch_entry, path):
            return path == ('b',)

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'copy',
            'from': '/a/b',
            'path': '/b',
        }]

        message = 'Cannot read from path "/a/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchReadAccessError, message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_read_key_func=_can_read_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b')

    def test_copy_with_missing_path(self):
        """Testing json_patch with copy op and missing destination path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'copy',
            'from': '/a',
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_copy_with_missing_from(self):
        """Testing json_patch with copy op and missing from path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'copy',
            'path': '/c',
        }]

        message = 'Missing key "from" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_copy_with_bad_from_path(self):
        """Testing json_patch with copy op and bad from path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'copy',
            'from': '/b',
            'path': '/c',
        }]

        message = (
            'Invalid from path "/b" for patch entry 0: Dictionary key "b" '
            'not found in "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_copy_with_bad_path(self):
        """Testing json_patch with copy op and bad destination path"""
        doc = {
            'a': 1,
            'b': 2,
        }

        patch = [{
            'op': 'copy',
            'from': '/a',
            'path': '/b/bad',
        }]

        message = (
            'Unable to add key "bad" to a non-dictionary/list in path '
            '"/b/bad" for patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b/bad')

        self.assertEqual(doc, {
            'a': 1,
            'b': 2,
        })

    def test_copy_with_invalid_from_path_syntax(self):
        """Testing json_patch with copy op and invalid from path syntax"""
        doc = {}
        patch = [{
            'op': 'copy',
            'from': 'b',
            'path': '/b',
        }]

        message = (
            'Syntax error in from path "b" for patch entry 0: Paths must '
            'either be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_copy_with_invalid_path_syntax(self):
        """Testing json_patch with copy op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'copy',
            'from': '/b',
            'path': 'b',
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must '
            'either be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_move_with_dict_key(self):
        """Testing json_patch with move op and dictionary key"""
        doc = {
            'a': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a',
                    'path': '/b'
                }]),
            {
                'b': 1,
            })
        self.assertEqual(doc, {
            'a': 1,
        })

    def test_move_with_array_index(self):
        """Testing json_patch with move op and array index"""
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a/1',
                    'path': '/a/0'
                }]),
            {
                'a': [2, 1, 3],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_move_with_array_index_end(self):
        """Testing json_patch with move op and array index `-` (end of array)
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a/1',
                    'path': '/a/-'
                }]),
            {
                'a': [1, 3, 2],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_move_with_from_array_index_end(self):
        """Testing json_patch with move op and "from" array index `-` (end of
        array)
        """
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'move',
            'from': '/a/-',
            'path': '/a/0'
        }]

        message = (
            'Cannot perform operation "move" from end of list at "/a/-" for '
            'patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/-')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_move_with_array_index_to_dict_key(self):
        """Testing json_patch with move op and array index copied to dictionary
        key
        """
        doc = {
            'a': [1, 2, 3],
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a/1',
                    'path': '/b'
                }]),
            {
                'a': [1, 3],
                'b': 2,
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_move_with_dict_key_to_array_index(self):
        """Testing json_patch with move op and dictionary key moved to array
        index
        """
        doc = {
            'a': [1, 2, 3],
            'b': 100,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/b',
                    'path': '/a/1'
                }]),
            {
                'a': [1, 100, 2, 3],
            })
        self.assertEqual(doc, {
            'a': [1, 2, 3],
            'b': 100,
        })

    def test_move_with_same_paths(self):
        """Testing json_patch with move op and same source and destination
        paths
        """
        doc = {
            'a': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a',
                    'path': '/a'
                }]),
            {
                'a': 1,
            })
        self.assertEqual(doc, {
            'a': 1,
        })

    def test_move_with_can_write_key_func_and_allowed(self):
        """Testing json_patch with move op and can_write_key_func and key
        allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path in (('a', 'b'), ('b',))

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'move',
                    'from': '/a/b',
                    'path': '/b',
                }],
                can_write_key_func=_can_write_key),
            {
                'a': {},
                'b': 1,
            })

    def test_move_with_can_write_key_func_and_not_allowed(self):
        """Testing json_patch with move op and can_write_key_func and key
        not allowed
        """
        def _can_write_key(doc, patch_entry, path):
            return path in ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'move',
            'from': '/a/b',
            'path': '/b',
        }]

        message = 'Cannot write to path "/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchWriteAccessError,
                                      message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_write_key_func=_can_write_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

    def test_move_with_missing_path(self):
        """Testing json_patch with move op and missing destination path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'move',
            'from': '/a',
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_move_with_missing_from(self):
        """Testing json_patch with move op and missing from path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'move',
            'path': '/c',
        }]

        message = 'Missing key "from" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_move_with_bad_from_path(self):
        """Testing json_patch with move op and bad from path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'move',
            'from': '/b',
            'path': '/c',
        }]

        message = (
            'Invalid from path "/b" for patch entry 0: Dictionary key "b" '
            'not found in "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b')

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_move_with_bad_path(self):
        """Testing json_patch with move op and bad destination path"""
        doc = {
            'a': 1,
            'b': 2,
        }
        patch = [{
            'op': 'move',
            'from': '/a',
            'path': '/b/bad',
        }]

        message = (
            'Unable to add key "bad" to a non-dictionary/list in path '
            '"/b/bad" for patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b/bad')

        self.assertEqual(doc, {
            'a': 1,
            'b': 2,
        })

    def test_move_with_invalid_from_path_syntax(self):
        """Testing json_patch with move op and invalid from path syntax"""
        doc = {}
        patch = [{
            'op': 'move',
            'from': 'b',
            'path': '/b',
        }]

        message = (
            'Syntax error in from path "b" for patch entry 0: Paths must '
            'either be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_move_with_invalid_path_syntax(self):
        """Testing json_patch with move op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'move',
            'from': '/b',
            'path': 'b',
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must '
            'either be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')

    def test_move_with_moving_into_child(self):
        """Testing json_patch with move op and attempting to move into child of
        path
        """
        doc = {
            'a': {
                'b': {
                    'c': {},
                },
            },
        }
        patch = [{
            'op': 'move',
            'from': '/a/b',
            'path': '/a/b/c',
        }]

        message = 'Cannot move values into their own children at patch entry 0'

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b')

        self.assertEqual(doc, {
            'a': {
                'b': {
                    'c': {},
                },
            },
        })

    def test_test_with_matching_value(self):
        """Testing json_patch with test op and matching value"""
        doc = {
            'a': 1,
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'test',
                    'path': '/a',
                    'value': 1,
                }]),
            {
                'a': 1,
            })

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_test_with_missing_path(self):
        """Testing json_patch with test op and missing path"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'test',
            'value': 1,
        }]

        message = 'Missing key "path" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_test_with_array_index_end(self):
        """Testing json_patch with test op and array index `-` (end of array)
        """
        doc = {
            'a': [1, 2, 3],
        }
        patch = [{
            'op': 'test',
            'path': '/a/-',
            'value': 1,
        }]

        message = (
            'Cannot perform operation "test" on end of list at "/a/-" for '
            'patch entry 0'
        )

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/-')

        self.assertEqual(doc, {
            'a': [1, 2, 3],
        })

    def test_test_with_missing_value(self):
        """Testing json_patch with test op and missing value"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'test',
            'path': '/a',
        }]

        message = 'Missing key "value" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_test_without_matching_value(self):
        """Testing json_patch with test op and non-matching value"""
        doc = {
            'a': 1,
        }
        patch = [{
            'op': 'test',
            'path': '/a',
            'value': 2,
        }]

        message = \
            'Test failed for path "/a" at patch entry 0. Expected 2 and got 1.'

        with self.assertRaisesMessage(JSONPatchTestError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)

        self.assertEqual(doc, {
            'a': 1,
        })

    def test_test_with_can_read_key_func_and_allowed(self):
        """Testing json_patch with test op and can_read_key_func and key
        allowed
        """
        def _can_read_key(doc, patch_entry, path):
            return path == ('a', 'b')

        doc = {
            'a': {
                'b': 1,
            },
        }

        self.assertEqual(
            json_patch(
                doc=doc,
                patch=[{
                    'op': 'test',
                    'path': '/a/b',
                    'value': 1,
                }],
                can_read_key_func=_can_read_key),
            {
                'a': {
                    'b': 1,
                },
            })

    def test_test_with_can_read_key_func_and_not_allowed(self):
        """Testing json_patch with test op and can_read_key_func and key
        not allowed
        """
        def _can_read_key(doc, patch_entry, path):
            return path == ('a', 'c')

        doc = {
            'a': {
                'b': 1,
            },
        }
        patch = [{
            'op': 'test',
            'path': '/a/b',
            'value': 1,
        }]

        message = 'Cannot read from path "/a/b" for patch entry 0'

        with self.assertRaisesMessage(JSONPatchReadAccessError, message) as cm:
            json_patch(doc=doc,
                       patch=patch,
                       can_read_key_func=_can_read_key)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a/b')

    def test_test_with_dict_missing_key(self):
        """Testing json_patch with test op and dictionary with missing key"""
        doc = {}
        patch = [{
            'op': 'test',
            'path': '/a',
            'value': 1,
        }]

        message = (
            'Invalid path "/a" for patch entry 0: Dictionary key "a" not '
            'found in "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/a')

        self.assertEqual(doc, {})

    def test_test_with_bad_path(self):
        """Testing json_patch with test op and bad destination path"""
        doc = {
            'a': 1,
            'b': 2,
        }
        patch = [{
            'op': 'test',
            'path': '/b/bad',
            'value': 1,
        }]

        message = 'Cannot resolve path within unsupported type "int" at "/b"'

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, '/b/bad')

        self.assertEqual(doc, {
            'a': 1,
            'b': 2,
        })

    def test_test_with_invalid_path_syntax(self):
        """Testing json_patch with test op and invalid path syntax"""
        doc = {}
        patch = [{
            'op': 'test',
            'path': 'b',
            'value': 1,
        }]

        message = (
            'Syntax error in path "b" for patch entry 0: Paths must '
            'either be empty or start with a "/"'
        )

        with self.assertRaisesMessage(JSONPatchPathError, message) as cm:
            json_patch(doc=doc, patch=patch)

        e = cm.exception
        self.assertEqual(e.doc, doc)
        self.assertEqual(e.patch, patch)
        self.assertEqual(e.patch_entry_index, 0)
        self.assertEqual(e.path, 'b')


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
                    '"%s" at "/a/b"'
                    % six.text_type.__name__
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

        message = '%r is not a valid list index in "/a/b"' % 'c'

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

        message = (
            'Cannot resolve path within unsupported type "%s" at "/a/b"'
            % six.text_type.__name__
        )

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

        message = '%r is not a valid list index in "/a/b"' % 'c'

        with self.assertRaisesMessage(JSONPointerSyntaxError, message):
            json_resolve_pointer(obj, '/a/b/c')
