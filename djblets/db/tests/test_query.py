from __future__ import unicode_literals

from django.db.models.query_utils import Q
from django.utils import six

from djblets.db.query import prefix_q
from djblets.testing.testcases import TestCase


class PrefixTests(TestCase):
    """Tests for djblets.db.query.prefix_q."""

    def test_simple(self):
        """Testing prefix_q prefixes simple expressions"""
        self.assertEqual(
            six.text_type(prefix_q('fk', Q(hello='goodbye'))),
            six.text_type(Q(fk__hello='goodbye')))

    def test_nested(self):
        """Testing prefix_q prefixes nested expressions"""
        self.assertEqual(
            six.text_type(prefix_q(
                'fk',
                Q(foo='foo') |
                (Q(bar='bar') &
                 Q(baz='baz')))),
            six.text_type(
                Q(fk__foo='foo') |
                (Q(fk__bar='bar') &
                 Q(fk__baz='baz'))))

    def test_bytestring_result(self):
        """Testing that prefix_q generates byte strings for key names"""
        q = prefix_q('fk', Q(foo='bar'))
        self.assertEqual(len(q.children), 1)
        self.assertIs(type(q.children[0]), tuple)
        self.assertIsInstance(q.children[0][0], six.binary_type)
