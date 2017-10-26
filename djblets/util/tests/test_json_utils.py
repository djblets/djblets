"""Unit tests for djblets.util.json_utils."""

from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.util.json_utils import JSONPatchError, json_merge_patch


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
