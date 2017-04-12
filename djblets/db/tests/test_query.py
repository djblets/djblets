from __future__ import unicode_literals

from django.contrib.auth.models import User

from djblets.db.query import chainable_select_related_queryset
from djblets.testing.testcases import TestCase


class ChainableSelectRelatedQuerySetTests(TestCase):
    """Tests for djblets.db.query.chainable_select_related_queryset."""

    def test_select_related_with_new_fields(self):
        """Testing chainable_select_related_queryset with
        select_related(field, ...)
        """
        queryset = User.objects.select_related('foo')
        queryset = chainable_select_related_queryset(queryset)
        queryset = queryset.select_related('foo__bar', 'baz')
        queryset = queryset.select_related('foobar', 'baz')

        self.assertEqual(
            queryset.query.select_related,
            {
                'foo': {
                    'bar': {},
                },
                'baz': {},
                'foobar': {},
            })

    def test_select_related_with_new_no_args(self):
        """Testing chainable_select_related_queryset with select_related()"""
        queryset = User.objects.select_related('foo')
        queryset = chainable_select_related_queryset(queryset)
        queryset = queryset.select_related()

        self.assertTrue(queryset.query.select_related)

    def test_select_related_with_none(self):
        """Testing chainable_select_related_queryset with select_related(None)
        """
        queryset = User.objects.select_related('foo')
        queryset = chainable_select_related_queryset(queryset)
        queryset = queryset.select_related(None)

        self.assertFalse(queryset.query.select_related)
