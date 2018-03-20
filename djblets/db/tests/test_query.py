from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from django.utils import six

from djblets.db.query import chainable_select_related_queryset, prefix_q
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


class PrefixTests(TestCase):
    """Tests for djblets.db.query.prefix_q."""

    def test_simple(self):
        """Testing prefix_q prefixes simple expressions"""
        self.assertEqual(
            str(prefix_q('fk', Q(hello='goodbye'))),
            str(Q(fk__hello='goodbye')))

    def test_nested(self):
        """Testing prefix_q prefixes nested expressions"""
        self.assertEqual(
            str(prefix_q('fk',
                         Q(foo='foo') |
                         (Q(bar='bar') &
                          Q(baz='baz')))),
            str(Q(fk__foo='foo') |
                (Q(fk__bar='bar') &
                 Q(fk__baz='baz'))))

    def test_bytestring_result(self):
        """Testing that prefix_q generates byte strings for key names"""
        q = prefix_q('fk', Q(foo='bar'))
        self.assertEqual(len(q.children), 1)
        self.assertIs(type(q.children[0]), tuple)
        self.assertIsInstance(q.children[0][0], str)
