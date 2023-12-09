"""Unit tests for djblets.db.query_comparator.

Version Added:
    3.4
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import Group, User
from django.db.models import Count, Exists, F, OuterRef, Q, Value

from djblets.db.query_catcher import CatchQueriesContext
from djblets.db.query_comparator import (compare_queries,
                                         _format_node,
                                         _normalize_q)
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries


class CompareQueriesTests(TestModelsLoaderMixin, TestCase):
    """Unit tests for djblets.db.query_comparator.compare_queries.

    Version Added:
        3.4
    """

    maxDiff = None

    _extra_ws_re = re.compile(r'\s{2,}')

    def test_with_select_q_and_match(self) -> None:
        """Testing compare_queries with SELECT and Q() and match"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'where': Q(is_active=True),
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.filter(is_active=True))

        self.assertFalse(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'])
        self.assertEqual(ctx['query_mismatches'], [])

    def test_with_match_complex(self) -> None:
        """Testing compare_queries with match and complex query"""
        queries: ExpectedQueries = [
            {
                'annotations': {'__count': Count('*')},
                'model': User,

                'subqueries': [
                    {
                        'distinct': True,
                        'extra': {
                            'username': (
                                'select username from auth_user where id=%s',
                                [0],
                            ),
                        },
                        'extra_tables': ('auth_group',),
                        'join_types': {
                            'djblets_privacy_storedconsentdata': 'INNER JOIN',
                        },
                        'model': User,
                        'num_joins': 1,
                        'only_fields': {'username'},
                        'subquery': True,
                        'tables': {
                            'auth_user',
                            'djblets_privacy_storedconsentdata',
                        },
                        'where': Q(~Q(__Exists__subquery__=1) &
                                   Q(storedconsentdata__pk__gt=0)),

                        'subqueries': [
                            {
                                'annotations': {
                                    'a': Value(1),
                                },
                                'limit': 2,
                                'model': User,
                                'offset': 1,
                                'subquery': True,
                                'values_select': ('pk',),
                                'where': Q(Q(pk=OuterRef('pk')) &
                                           Q(username='test')),
                            },
                        ],
                    },
                ],
            },
        ]

        with compare_queries(queries) as ctx:
            count = (
                User.objects
                .filter(
                    ~Exists(
                        User.objects
                        .filter(Q(pk=OuterRef('pk')) &
                                Q(username='test'))
                        .values('pk')[1:2]
                    ) &
                    Q(storedconsentdata__pk__gt=0)
                )
                .select_related('storedconsentdata')
                .extra(
                    select={
                        'username': ('select username from auth_user'
                                     ' where id=%s'),
                    },
                    select_params=(0,),
                    tables=['auth_group'])
                .order_by('username')
                .only('username')
                .distinct()
                .count()
            )

        self.assertEqual(count, 0)
        self.assertEqual(
            ctx,
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 1,
                'num_expected_queries': 1,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })

    def test_with_mismatch_distinct(self) -> None:
        """Testing compare_queries with mismatch and distinct"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.distinct())

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': 'True',
                    'expected_value': 'False',
                    'name': 'distinct',
                    'raw_executed_value': True,
                    'raw_expected_value': False,
                },
            ])

    def test_with_mismatch_extra(self) -> None:
        """Testing compare_queries with mismatch and extra"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.extra(
                select={
                    'username': 'select username from auth_user where id=%s',
                },
                select_params=(0,)))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': (
                        "{'username': ('select username from auth_user"
                        " where id=%s', [0])}"
                    ),
                    'expected_value': '{}',
                    'name': 'extra',
                    'raw_executed_value': {
                        'username': (
                            'select username from auth_user where id=%s',
                            [0],
                        ),
                    },
                    'raw_expected_value': {},
                },
            ])

    def test_with_mismatch_extra_order_by(self) -> None:
        """Testing compare_queries with mismatch and extra_order_by"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.extra(order_by=['-pk']))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "['-pk']",
                    'expected_value': '()',
                    'name': 'extra_order_by',
                    'raw_executed_value': ['-pk'],
                    'raw_expected_value': (),
                },
            ])

    def test_with_mismatch_extra_tables(self) -> None:
        """Testing compare_queries with mismatch and extra_tables"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.extra(tables=['auth_group']))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "('auth_group',)",
                    'expected_value': '()',
                    'name': 'extra_tables',
                    'raw_executed_value': ('auth_group',),
                    'raw_expected_value': (),
                },
            ])

    def test_with_mismatch_joins(self) -> None:
        """Testing compare_queries with mismatch and joins"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(
                User.objects
                .filter(Q(storedconsentdata__pk__gt=0))
            )

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': '1',
                    'expected_value': '0',
                    'name': 'num_joins',
                    'raw_executed_value': 1,
                    'raw_expected_value': 0,
                },
                {
                    'executed_value': (
                        "{'auth_user', 'djblets_privacy_storedconsentdata'}"
                    ),
                    'expected_value': "{'auth_user'}",
                    'name': 'tables',
                    'raw_executed_value': {
                        'auth_user',
                        'djblets_privacy_storedconsentdata',
                    },
                    'raw_expected_value': {'auth_user'},
                },
                {
                    'executed_value': (
                        "{'djblets_privacy_storedconsentdata':"
                        " 'INNER JOIN'}"
                    ),
                    'expected_value': '{}',
                    'name': 'join_types',
                    'raw_executed_value': {
                        'djblets_privacy_storedconsentdata': 'INNER JOIN',
                    },
                    'raw_expected_value': {},
                },
                {
                    'executed_value': 'Q(storedconsentdata__pk__gt=0)',
                    'expected_value': 'Q()',
                    'name': 'where',
                    'raw_executed_value': Q(storedconsentdata__pk__gt=0),
                    'raw_expected_value': Q(),
                },
            ])

    def test_with_mismatch_limit(self) -> None:
        """Testing compare_queries with mismatch and limit"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'limit': 1,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.all()[:2])

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': '2',
                    'expected_value': '1',
                    'name': 'limit',
                    'raw_executed_value': 2,
                    'raw_expected_value': 1,
                },
            ])

    def test_with_mismatch_offset(self) -> None:
        """Testing compare_queries with mismatch and offset"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'offset': 2,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.all()[1:])

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': '1',
                    'expected_value': '2',
                    'name': 'offset',
                    'raw_executed_value': 1,
                    'raw_expected_value': 2,
                },
            ])

    def test_with_mismatch_only_fields(self) -> None:
        """Testing compare_queries with mismatch and only_field"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'only_fields': {'id'},
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.only('pk', 'username'))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "{'id', 'username'}",
                    'expected_value': "{'id'}",
                    'name': 'only_fields',
                    'raw_executed_value': {'id', 'username'},
                    'raw_expected_value': {'id'},
                },
            ])

    def test_with_mismatch_order_by(self) -> None:
        """Testing compare_queries with mismatch and order_by"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'order_by': ('pk',),
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.order_by('email'))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "('email',)",
                    'expected_value': "('pk',)",
                    'name': 'order_by',
                    'raw_executed_value': ('email',),
                    'raw_expected_value': ('pk',),
                },
            ])

    def test_with_mismatch_select_for_update(self) -> None:
        """Testing compare_queries with mismatch and select_for_update"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.select_for_update())

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': 'True',
                    'expected_value': 'False',
                    'name': 'select_for_update',
                    'raw_executed_value': True,
                    'raw_expected_value': False,
                },
            ])

    def test_with_mismatch_select_related(self) -> None:
        """Testing compare_queries with mismatch and select_related"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'select_related': {'group'},
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.select_related('storedconsentdata'))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "{'storedconsentdata'}",
                    'expected_value': "{'group'}",
                    'name': 'select_related',
                    'raw_executed_value': {'storedconsentdata'},
                    'raw_expected_value': {'group'},
                },
            ])

    def test_with_mismatch_subqueries(self) -> None:
        """Testing compare_queries with mismatch and subqueries"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'subqueries': [
                    {
                        'model': User,
                        'subqueries': [
                            {
                                'model': User,
                            },
                        ],
                    },
                ],
            },
        ]

        with compare_queries(queries) as ctx:
            count = (
                User.objects
                .filter(Exists(User.objects.filter(pk=OuterRef('pk'))))
                .distinct()
                .count()
            )

        self.assertEqual(count, 0)

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "{'__count': Count('*')}",
                    'expected_value': '{}',
                    'name': 'annotations',
                    'raw_executed_value': {'__count': Count('*')},
                    'raw_expected_value': {},
                },
            ])

        # Check the distinct subquery.
        subqueries = mismatch['subqueries']
        assert subqueries is not None
        self.assertTrue(subqueries['has_mismatches'])
        self.assertEqual(subqueries['num_executed_queries'], 1)
        self.assertEqual(subqueries['num_expected_queries'], 1)
        self.assertFalse(subqueries['query_count_mismatch'])

        subquery_mismatches = subqueries['query_mismatches']
        self.assertEqual(len(subquery_mismatches), 1)

        subquery_mismatch = subquery_mismatches[0]
        self.assertIsNotNone(subquery_mismatch['executed_query'])
        self.assertEqual(subquery_mismatch['index'], 0)
        self.assertIsNone(subquery_mismatch['note'])
        self.assertIsNone(subquery_mismatch['traceback'])
        self.assertEqual(
            subquery_mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': 'True',
                    'expected_value': 'False',
                    'name': 'distinct',
                    'raw_executed_value': True,
                    'raw_expected_value': False,
                },
                {
                    'executed_value': 'True',
                    'expected_value': 'False',
                    'name': 'subquery',
                    'raw_executed_value': True,
                    'raw_expected_value': False,
                },
                {
                    'executed_value': 'Q(__Exists__subquery__=1)',
                    'expected_value': 'Q()',
                    'name': 'where',
                    'raw_executed_value': Q(__Exists__subquery__=1),
                    'raw_expected_value': Q(),
                },
            ])

        # Check the Exists subquery.
        subqueries = subquery_mismatch['subqueries']
        assert subqueries is not None
        self.assertTrue(subqueries['has_mismatches'])
        self.assertEqual(subqueries['num_executed_queries'], 1)
        self.assertEqual(subqueries['num_expected_queries'], 1)
        self.assertFalse(subqueries['query_count_mismatch'])

        subquery_mismatches = subqueries['query_mismatches']
        self.assertEqual(len(subquery_mismatches), 1)

        subquery_mismatch = subquery_mismatches[0]
        self.assertIsNotNone(subquery_mismatch['executed_query'])
        self.assertEqual(subquery_mismatch['index'], 0)
        self.assertIsNone(subquery_mismatch['note'])
        self.assertIsNone(subquery_mismatch['traceback'])
        self.assertEqual(
            subquery_mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "{'a': Value(1)}",
                    'expected_value': '{}',
                    'name': 'annotations',
                    'raw_executed_value': {'a': Value(1)},
                    'raw_expected_value': {},
                },
                {
                    'executed_value': 'True',
                    'expected_value': 'False',
                    'name': 'subquery',
                    'raw_executed_value': True,
                    'raw_expected_value': False,
                },
                {
                    'executed_value': '1',
                    'expected_value': 'None',
                    'name': 'limit',
                    'raw_executed_value': 1,
                    'raw_expected_value': None,
                },
                {
                    'executed_value': "Q(pk=OuterRef('pk'))",
                    'expected_value': 'Q()',
                    'name': 'where',
                    'raw_executed_value': Q(pk=OuterRef('pk')),
                    'raw_expected_value': Q(),
                },
            ])
        self.assertEqual(
            subquery_mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })

    def test_with_mismatch_type(self) -> None:
        """Testing compare_queries with mismatch and type"""
        queries: ExpectedQueries = [
            {
                'model': User,
            },
        ]

        with compare_queries(queries) as ctx:
            User.objects.create(username='test-user')

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "'INSERT'",
                    'expected_value': "'SELECT'",
                    'name': 'type',
                    'raw_executed_value': 'INSERT',
                    'raw_expected_value': 'SELECT',
                },
            ])

    def test_with_mismatch_values_select(self) -> None:
        """Testing compare_queries with mismatch and values_select"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'values_select': ('pk',),
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.values('username', 'email'))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': "('username', 'email')",
                    'expected_value': "('pk',)",
                    'name': 'values_select',
                    'raw_executed_value': ('username', 'email'),
                    'raw_expected_value': ('pk',),
                },
            ])

    def test_with_mismach_where(self) -> None:
        """Testing compare_queries with mismatch and where"""
        queries: ExpectedQueries = [
            {
                'model': User,
                'where': Q(username='test'),
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.filter(is_active=True))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': 'Q(is_active=True)',
                    'expected_value': "Q(username='test')",
                    'name': 'where',
                    'raw_executed_value': Q(is_active=True),
                    'raw_expected_value': Q(username='test'),
                },
            ])

    def test_with_note(self) -> None:
        """Testing compare_queries with mismatch and note"""
        queries: ExpectedQueries = [
            {
                'model': Group,
            },
        ]

        with compare_queries(queries) as ctx:
            list(User.objects.filter(is_active=True))

        self.assertTrue(ctx['has_mismatches'])
        self.assertEqual(ctx['num_executed_queries'], 1)
        self.assertEqual(ctx['num_expected_queries'], 1)
        self.assertFalse(ctx['query_count_mismatch'], 1)

        mismatches = ctx['query_mismatches']
        self.assertEqual(len(mismatches), 1)

        mismatch = mismatches[0]
        self.assertIsNotNone(mismatch['executed_query'])
        self.assertEqual(mismatch['index'], 0)
        self.assertIsNone(mismatch['note'])
        self.assertIsNotNone(mismatch['traceback'])
        self.assertEqual(
            mismatch['subqueries'],
            {
                '_unchecked_mismatched_attrs': set(),
                'has_mismatches': False,
                'num_executed_queries': 0,
                'num_expected_queries': 0,
                'query_count_mismatch': False,
                'query_mismatches': [],
            })
        self.assertEqual(
            mismatch['mismatched_attrs'],
            [
                {
                    'executed_value': repr(User),
                    'expected_value': repr(Group),
                    'name': 'model',
                    'raw_executed_value': User,
                    'raw_expected_value': Group,
                },
                {
                    'executed_value': "{'auth_user'}",
                    'expected_value': "{'auth_group'}",
                    'name': 'tables',
                    'raw_executed_value': {'auth_user'},
                    'raw_expected_value': {'auth_group'},
                },
                {
                    'executed_value': 'Q(is_active=True)',
                    'expected_value': 'Q()',
                    'name': 'where',
                    'raw_executed_value': Q(is_active=True),
                    'raw_expected_value': Q(),
                },
            ])


class FormatNodeTests(TestCase):
    """Unit tests for djblets.db.query_comparator._format_node.

    Version Added:
        3.4
    """

    ######################
    # Instance variables #
    ######################

    catch_ctx: CatchQueriesContext

    def setUp(self) -> None:
        super().setUp()

        self.catch_ctx = CatchQueriesContext(executed_queries=[],
                                             queries_to_qs={})

    def tearDown(self) -> None:
        self.catch_ctx = None  # type: ignore

        super().tearDown()

    def test_with_nested_q(self) -> None:
        """Testing _format_node with single nested Qs"""
        self.assertEqual(
            _format_node(_normalize_q(Q(a=1)),
                         catch_ctx=self.catch_ctx),
            'Q(a=1)')

    def test_with_nested_q_negated_start(self) -> None:
        """Testing _format_node with single nested Qs and negated at start"""
        self.assertEqual(
            _format_node(_normalize_q(~Q(a=1)),
                         catch_ctx=self.catch_ctx),
            '~Q(a=1)')

    def test_with_nested_q_negated_start_2(self) -> None:
        """Testing _format_node with single nested Qs and negated at start"""
        self.assertEqual(
            _format_node(_normalize_q(~Q(group__in=[1])),
                         catch_ctx=self.catch_ctx),
            '~Q(group__in=[1])')

    def test_with_nested_q_negated_all(self) -> None:
        """Testing _format_node with single nested Qs and all negated states.
        """
        print(_normalize_q(~Q(~Q(~Q(~Q(a=1))))))
        self.assertEqual(
            _format_node(_normalize_q(~Q(~Q(~Q(~Q(a=1))))),
                         catch_ctx=self.catch_ctx),
            '~Q(\n'
            ' ~Q(\n'
            '  ~Q(\n'
            '   ~Q(a=1))))')

    def test_with_negated_with_n_children_and(self) -> None:
        """Testing _format_node with negated Q with nested children with AND"""
        self.assertEqual(
            _format_node(_normalize_q(~Q(Q(a=1) & Q(b=2))),
                         catch_ctx=self.catch_ctx),
            '~Q(\n'
            '   Q(a=1)\n'
            ' & Q(b=2))')

    def test_with_negated_with_n_children_or(self) -> None:
        """Testing _format_node with negated Q with nested children with OR"""
        self.assertEqual(
            _format_node(_normalize_q(~Q(Q(a=1) | Q(b=2))),
                         catch_ctx=self.catch_ctx),
            '~Q(\n'
            '   Q(a=1)\n'
            ' | Q(b=2))')

    def test_with_negated_with_subquery(self) -> None:
        """Testing _format_node with negated Q with nested subquery"""
        self.assertEqual(
            _format_node(_normalize_q(~Q(Exists(User.objects.all()))),
                         catch_ctx=self.catch_ctx),
            '~Q(__Exists__subquery__=1)')

    def test_with_subquery(self) -> None:
        """Testing _format_node with subquery"""
        self.assertEqual(
            _format_node(
                _normalize_q(
                    ~Q(Exists(User.objects.all()) |
                       ~Exists(User.objects.none()))),
                catch_ctx=self.catch_ctx),
            '~Q(\n'
            '   Q(__Exists__subquery__=1)\n'
            ' | ~Q(__Exists__subquery__=2))')

    def test_with_subquery_nested(self) -> None:
        """Testing _format_node with subquery and nested expressions"""
        self.assertEqual(
            _format_node(
                _normalize_q(
                    Exists(User.objects.filter(
                        Q(is_active=True) &
                        ~Q(username='test'))) |
                    ~Exists(User.objects.filter(
                        Q(email__contains='@hotmail.com') &
                        ~Q(first_name='Bob')))),
                catch_ctx=self.catch_ctx),
            'Q(\n'
            '   Q(__Exists__subquery__=1)\n'
            ' | ~Q(__Exists__subquery__=2))')

    def test_with_f(self) -> None:
        """Testing _format_node with F() expression"""
        self.assertEqual(
            _format_node(
                _normalize_q(Q(a=F('b') + 3)),
                catch_ctx=self.catch_ctx),
            "Q(a=F('b') + 3)")

    def test_with_complex(self) -> None:
        """Testing _format_node with complex nested tree of Qs and Subqueries
        """
        self.assertEqual(
            _format_node(
                _normalize_q(
                    Q(Q(Q(a=1) &
                        (Q(Q(b=2)) |
                         Q(c=3) | Q())) |
                      ~Q(Q(Q(d=4)) |
                         (Q(Exists(User.objects.all())) &
                          ~Exists(User.objects.none()) &
                          Q(e=5) &
                          Q() &
                          ~Q() &
                          ~Q(Q(Q(f=F('g') + 6))))))),
                catch_ctx=self.catch_ctx),
            "Q(\n"
            "   Q(\n"
            "      Q(a=1)\n"
            "    & Q(\n"
            "         Q(b=2)\n"
            "       | Q(c=3)))\n"
            " | ~Q(\n"
            "      Q(d=4)\n"
            "    | Q(\n"
            "         Q(__Exists__subquery__=1)\n"
            "       & ~Q(__Exists__subquery__=2)\n"
            "       & Q(e=5)\n"
            "       & ~Q(f=F('g') + 6))))")


class NormalizeQTests(TestCase):
    """Unit tests for djblets.db.query_comparator._normalize_q.

    Version Added:
        3.4
    """

    def test_with_nested_q(self) -> None:
        """Testing _normalize_q with single nested Qs"""
        norm_q = _normalize_q(Q(Q(Q(Q(a=1)))))
        self.assertEqual(norm_q, Q(a=1))
        self.assertEqual(repr(norm_q), "<Q: (AND: ('a', 1))>")

    def test_with_nested_q_and_empty(self) -> None:
        """Testing _normalize_q with nested Qs and empty Qs"""
        norm_q = _normalize_q(Q(Q(Q(Q(a=1) & Q()))))
        self.assertEqual(norm_q, Q(a=1))
        self.assertEqual(repr(norm_q), "<Q: (AND: ('a', 1))>")

    def test_with_nested_q_negated_start(self) -> None:
        """Testing _normalize_q with single nested Qs and negated at start"""
        norm_q = _normalize_q(~Q(Q(Q(Q(a=1)))))
        self.assertEqual(norm_q, ~Q(a=1))
        self.assertEqual(repr(norm_q), "<Q: (NOT (AND: ('a', 1)))>")

    def test_with_nested_q_negated_start_2(self) -> None:
        """Testing _normalize_q with single nested Qs and negated at start"""
        norm_q = _normalize_q(~Q(Q(group__in=[1])))
        self.assertEqual(norm_q, ~Q(group__in=[1]))
        self.assertEqual(repr(norm_q), "<Q: (NOT (AND: ('group__in', [1])))>")

    def test_with_nested_q_negated_middle(self) -> None:
        """Testing _normalize_q with single nested Qs and negated in the middle
        """
        norm_q = _normalize_q(Q(Q(~Q(Q(a=1)))))
        self.assertEqual(norm_q, ~Q(a=1))
        self.assertEqual(repr(norm_q), "<Q: (NOT (AND: ('a', 1)))>")

    def test_with_nested_q_negated_end(self) -> None:
        """Testing _normalize_q with single nested Qs and negated at the end
        """
        norm_q = _normalize_q(Q(Q(Q(~Q(a=1)))))
        self.assertEqual(norm_q, ~Q(a=1))
        self.assertEqual(repr(norm_q), "<Q: (NOT (AND: ('a', 1)))>")

    def test_with_nested_q_negated_all(self) -> None:
        """Testing _normalize_q with single nested Qs and all negated states.
        """
        norm_q = _normalize_q(~Q(~Q(~Q(~Q(a=1)))))
        self.assertEqual(norm_q, ~Q(~Q(~Q(~Q(a=1)))))
        self.assertEqual(
            repr(norm_q),
            "<Q: (NOT (AND: (NOT (AND: (NOT (AND: (NOT (AND: ('a', 1)))))))))>"
        )

    def test_with_nested_q_negated_double(self) -> None:
        """Testing _normalize_q with single nested Qs and double-negated"""
        norm_q = _normalize_q(~Q(Q(Q(~Q(a=1)))))
        self.assertEqual(norm_q, ~Q(~Q(a=1)))
        self.assertEqual(repr(norm_q),
                         "<Q: (NOT (AND: (NOT (AND: ('a', 1)))))>")

    def test_with_negated_with_n_children_and(self) -> None:
        """Testing _normalize_q with negated Q with nested children with AND"""
        norm_q = _normalize_q(~Q(Q(a=1) & Q(b=2)))
        self.assertEqual(norm_q, ~Q(Q(a=1) & Q(b=2)))
        self.assertEqual(repr(norm_q),
                         "<Q: (NOT (AND: (AND: ('a', 1), ('b', 2))))>")

    def test_with_negated_with_n_children_or(self) -> None:
        """Testing _normalize_q with negated Q with nested children with OR"""
        norm_q = _normalize_q(~Q(Q(a=1) | Q(b=2)))
        self.assertEqual(norm_q, ~Q(Q(a=1) | Q(b=2)))
        self.assertEqual(repr(norm_q),
                         "<Q: (NOT (AND: (OR: ('a', 1), ('b', 2))))>")

    def test_with_negated_with_subquery(self) -> None:
        """Testing _normalize_q with negated Q with nested subquery"""
        norm_q = _normalize_q(~Q(Exists(User.objects.all())))
        self.assertEqual(norm_q, ~Q(__Exists__subquery__=1))
        self.assertEqual(repr(norm_q),
                         "<Q: (NOT (AND: ('__Exists__subquery__', 1)))>")

    def test_with_subquery(self) -> None:
        """Testing _normalize_q with subquery"""
        norm_q = _normalize_q(~Q(Exists(User.objects.all()) |
                                 ~Exists(User.objects.none())))
        self.assertEqual(norm_q,
                         ~Q(Q(__Exists__subquery__=1) |
                            ~Q(__Exists__subquery__=2)))
        self.assertEqual(
            repr(norm_q),
            "<Q: (NOT (AND: (OR: ('__Exists__subquery__', 1),"
            " (NOT (AND: ('__Exists__subquery__', 2))))))>")

    def test_with_subquery_nested(self) -> None:
        """Testing _normalize_q with subquery and nested expressions"""
        norm_q = _normalize_q(
            Exists(User.objects.filter(
                Q(is_active=True) &
                ~Q(username='test')
            )) |
            ~Exists(User.objects.filter(
                Q(email__contains='@hotmail.com') &
                ~Q(first_name='Bob')
            )))
        self.assertEqual(norm_q,
                         (Q(__Exists__subquery__=1) |
                          ~Q(__Exists__subquery__=2)))
        self.assertEqual(
            repr(norm_q),
            "<Q: (OR: ('__Exists__subquery__', 1),"
            " (NOT (AND: ('__Exists__subquery__', 2))))>")

    def test_with_complex(self) -> None:
        """Testing _normalize_q with complex nested tree of Qs and Subqueries
        """
        norm_q = _normalize_q(
            Q(Q(Q(a=1) & (Q(Q(b=2)) | Q(c=3) | Q())) |
              ~Q(Q(Q(d=4)) |
                 (Q(Exists(User.objects.all())) &
                  ~Exists(User.objects.none()) &
                  Q(e=5) &
                  Q() &
                  ~Q() &
                  ~Q(Q(f=6))))))
        self.assertEqual(
            norm_q,
            Q(Q(a=1) &
              Q(Q(b=2) | Q(c=3))) |
            ~Q(Q(d=4) |
               (Q(__Exists__subquery__=1) &
                ~Q(__Exists__subquery__=2) &
                (Q(e=5) & ~Q(f=6)))))
        self.assertEqual(
            repr(norm_q),
            "<Q: (OR: (AND: ('a', 1), (OR: ('b', 2), ('c', 3))),"
            " (NOT (AND: (OR: ('d', 4), (AND: ('__Exists__subquery__', 1),"
            " (NOT (AND: ('__Exists__subquery__', 2))),"
            " ('e', 5), (NOT (AND: ('f', 6))))))))>")
