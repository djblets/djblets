"""Unit tests for djblets.db.query_catcher.

Version Added:
    3.4
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, TYPE_CHECKING, Type

from django.db import models
from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.sql.subqueries import AggregateQuery

from djblets.db.query_catcher import (ExecutedQueryType,
                                      catch_queries)
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin

if TYPE_CHECKING:
    from djblets.db.query_catcher import (CatchQueriesContext,
                                          ExecutedQueryInfo,
                                          ExecutedSubQueryInfo)


class CapturedQueriesTestModel(models.Model):
    name = models.CharField(max_length=10)
    flag = models.BooleanField(default=True)


class CapturedQueriesRelTestModel(models.Model):
    # Set up a relation, but don't do anything if the test model deletes.
    # We don't want this interfering with our query tests.
    test = models.ForeignKey(CapturedQueriesTestModel,
                             on_delete=models.DO_NOTHING)


class CaptureQueriesTests(TestModelsLoaderMixin, TestCase):
    """Unit tests for djblets.db.query_catcher.catch_queries.

    Version Added:
        3.4
    """

    tests_app = 'djblets.db.tests'

    maxDiff = 10_000

    _extra_ws_re = re.compile(r'\s{2,}')

    def test_with_select(self) -> None:
        """Testing capture_queries with SELECT"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        with catch_queries() as ctx:
            objs = list(
                CapturedQueriesTestModel.objects
                .filter(Q(name__startswith='test') &
                        Q(flag=True))
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag" '
                ' FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE'
                '  ("djblets_db_capturedqueriestestmodel"."name"'
                '   LIKE test% ESCAPE \'\\\''
                '   AND "djblets_db_capturedqueriestestmodel"."flag")',
            ],
            q=(
                Q(Q(name__startswith='test') &
                  Q(flag=True))
            ))

        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0].name, 'test1')
        self.assertEqual(objs[1].name, 'test2')

    def test_with_insert(self) -> None:
        """Testing capture_queries with SELECT"""
        with catch_queries() as ctx:
            CapturedQueriesTestModel.objects.bulk_create([
                CapturedQueriesTestModel(name='test1'),
                CapturedQueriesTestModel(name='test2'),
            ])

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            query_type=ExecutedQueryType.INSERT,
            sql=[
                'INSERT INTO "djblets_db_capturedqueriestestmodel"'
                ' ("name", "flag")'
                ' VALUES (test1, True), (test2, True)',
            ])

    def test_with_delete(self) -> None:
        """Testing capture_queries with DELETE"""
        obj = CapturedQueriesTestModel.objects.create(name='test')
        obj_id = obj.pk

        with catch_queries() as ctx:
            obj.delete()

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            query_type=ExecutedQueryType.DELETE,
            sql=[
                'DELETE FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" IN (1)',
            ],
            q=Q(id__in=[obj_id]))

    def test_with_update(self) -> None:
        """Testing capture_queries with UPDATE"""
        obj = CapturedQueriesTestModel.objects.create(name='test')

        with catch_queries() as ctx:
            obj.flag = False
            obj.save(update_fields=('flag',))

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            query_type=ExecutedQueryType.UPDATE,
            sql=[
                'UPDATE "djblets_db_capturedqueriestestmodel"'
                ' SET "flag" = False'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" = 1',
            ],
            q=Q(pk=obj.pk))

    def test_with_multiple(self) -> None:
        """Testing capture_queries with multiple queries"""
        with catch_queries() as ctx:
            obj = CapturedQueriesTestModel.objects.create(name='test')
            obj.flag = False
            obj.save(update_fields=('flag',))

            list(CapturedQueriesTestModel.objects.all())

            obj.delete()

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 4)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            query_type=ExecutedQueryType.INSERT,
            sql=[
                'INSERT INTO "djblets_db_capturedqueriestestmodel"'
                ' ("name", "flag")'
                ' VALUES (test, True)',
            ])

        self._check_query(
            executed_queries[1],
            ctx=ctx,
            query_type=ExecutedQueryType.UPDATE,
            sql=[
                'UPDATE "djblets_db_capturedqueriestestmodel"'
                ' SET "flag" = False'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" = 1',
            ],
            q=Q(pk=1))

        self._check_query(
            executed_queries[2],
            ctx=ctx,
            query_type=ExecutedQueryType.SELECT,
            sql=[
                'SELECT "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel"',
            ])

        self._check_query(
            executed_queries[3],
            ctx=ctx,
            query_type=ExecutedQueryType.DELETE,
            sql=[
                'DELETE FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" IN (1)',
            ],
            q=Q(id__in=[1]))

    def test_with_annotation_subquery(self) -> None:
        """Testing capture_queries with annotation and Subquery"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            objs = list(
                CapturedQueriesTestModel.objects
                .filter(Q(name__startswith='test'))
                .annotate(sub=Subquery(
                    CapturedQueriesRelTestModel.objects
                    .filter(test=OuterRef('pk'))
                    .values('pk')
                ))
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag", '
                ' (SELECT U0."id"'
                '   FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '   WHERE'
                '    U0."test_id" ='
                '    ("djblets_db_capturedqueriestestmodel"."id")) AS "sub"'
                ' FROM "djblets_db_capturedqueriestestmodel" '
                ' WHERE'
                '  "djblets_db_capturedqueriestestmodel"."name"'
                '   LIKE test% ESCAPE \'\\\''
            ],

            # NOTE: Subquery() cannot be compared through equality checks.
            can_compare_q=False)

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=Subquery,
            q=Q(test=OuterRef('pk')))

        # Check the fetched objects from the query.
        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0].name, 'test1')
        self.assertEqual(objs[1].name, 'test2')

    def test_with_annotation_exists(self) -> None:
        """Testing capture_queries with annotation and Exists"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            objs = list(
                CapturedQueriesTestModel.objects
                .filter(Q(name__startswith='test'))
                .annotate(sub=Exists(
                    CapturedQueriesRelTestModel.objects
                    .filter(test=OuterRef('pk'))
                ))
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag", '
                ' EXISTS(SELECT 1 AS "a"'
                '  FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '  WHERE'
                '   U0."test_id" ='
                '   ("djblets_db_capturedqueriestestmodel"."id")'
                '  LIMIT 1) AS "sub"'
                ' FROM "djblets_db_capturedqueriestestmodel" '
                ' WHERE'
                '  "djblets_db_capturedqueriestestmodel"."name"'
                '   LIKE test% ESCAPE \'\\\''
            ],

            # NOTE: Exists() cannot be compared through equality checks.
            can_compare_q=False)

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=Exists,
            q=Q(test=OuterRef('pk')))

        # Check the fetched objects from the query.
        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0].name, 'test1')
        self.assertEqual(objs[1].name, 'test2')

    def test_with_aggregate_subquery(self) -> None:
        """Testing capture_queries with aggregates and Subquery"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[1]),
            CapturedQueriesRelTestModel(test=test_models[1]),
        ])

        with catch_queries() as ctx:
            # This query is a particular amount of nonsense. Don't worry
            # about it.
            list(
                CapturedQueriesTestModel.objects
                .filter(
                    Q(name__startswith='test') &
                    Q(pk__gt=Subquery(
                        CapturedQueriesRelTestModel.objects
                        .filter(test=OuterRef('pk'))
                        .annotate(some_value=Sum('pk') + 1)
                        .values('some_value')
                    ))
                )
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel" '
                ' WHERE'
                '  ("djblets_db_capturedqueriestestmodel"."name"'
                '    LIKE test% ESCAPE \'\\\' AND'
                '   "djblets_db_capturedqueriestestmodel"."id" > '
                '    (SELECT (SUM(U0."id") + 1) AS "some_value"'
                '      FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '      WHERE U0."test_id" ='
                '       ("djblets_db_capturedqueriestestmodel"."id")'
                '      GROUP BY U0."id", U0."test_id"))'
            ],

            # NOTE: Subquery() cannot be compared through equality checks.
            can_compare_q=False)

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=Subquery,
            q=Q(test=OuterRef('pk')))

    def test_with_filter_subquery_exists(self) -> None:
        """Testing capture_queries with filtering using Exists subqueries"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            objs = list(
                CapturedQueriesTestModel.objects
                .filter(
                    Q(name__startswith='test') &
                    Exists(
                        CapturedQueriesRelTestModel.objects
                        .filter(test=OuterRef('pk'))
                    )
                )
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel" '
                ' WHERE'
                '  ("djblets_db_capturedqueriestestmodel"."name"'
                '    LIKE test% ESCAPE \'\\\' AND'
                '   EXISTS(SELECT 1 AS "a"'
                '    FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '    WHERE U0."test_id" ='
                '     ("djblets_db_capturedqueriestestmodel"."id")'
                '    LIMIT 1))',
            ],

            # NOTE: Exists() cannot be compared through equality checks.
            can_compare_q=False)

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=Exists,
            q=Q(test=OuterRef('pk')))

        # Check the fetched objects from the query.
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].name, 'test1')

    def test_with_filter_subquery_q(self) -> None:
        """Testing capture_queries with filtering using Q subqueries"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            objs = list(
                CapturedQueriesTestModel.objects
                .filter(
                    Q(name__startswith='test') &
                    Q(pk__in=(
                        CapturedQueriesRelTestModel.objects
                        .values_list('pk', flat=True)
                    ))
                )
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT'
                ' "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel" '
                ' WHERE'
                '  ("djblets_db_capturedqueriestestmodel"."name"'
                '    LIKE test% ESCAPE \'\\\' AND'
                '   "djblets_db_capturedqueriestestmodel"."id" IN'
                '    (SELECT U0."id" FROM'
                '      "djblets_db_capturedqueriesreltestmodel" U0))',
            ],

            # NOTE: QuerySet() cannot be compared consistently through
            #       equality checks.
            can_compare_q=False)

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=QuerySet)

        # Check the fetched objects from the query.
        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0].name, 'test1')
        self.assertEqual(objs[1].name, 'test2')

    def test_with_distinct_count(self) -> None:
        """Testing capture_queries with distinct() and count()"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            count = (
                CapturedQueriesTestModel.objects
                .filter(name__startswith='test')
                .distinct()
                .count()
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT COUNT(*)'
                ' FROM'
                ' (SELECT DISTINCT'
                '   "djblets_db_capturedqueriestestmodel"."id" AS "col1",'
                '   "djblets_db_capturedqueriestestmodel"."name" AS "col2",'
                '   "djblets_db_capturedqueriestestmodel"."flag" AS "col3"'
                '  FROM "djblets_db_capturedqueriestestmodel"'
                '  WHERE "djblets_db_capturedqueriestestmodel"."name"'
                '   LIKE test% ESCAPE \'\\\') subquery'
            ])

        # Check the subqueries.
        self._check_subquery(
            executed_queries[0]['subqueries'][0],
            ctx=ctx,
            subquery_class=AggregateQuery,
            q=Q(name__startswith='test'))

        # Check the fetched count.
        self.assertEqual(count, 2)

    def test_with_subqueries_complex(self) -> None:
        """Testing capture_queries with complex subqueries"""
        CapturedQueriesTestModel.objects.bulk_create([
            CapturedQueriesTestModel(name='test1'),
            CapturedQueriesTestModel(name='test2'),
        ])

        # Re-fetch to guarantee IDs.
        test_models = list(CapturedQueriesTestModel.objects.all())

        CapturedQueriesRelTestModel.objects.bulk_create([
            CapturedQueriesRelTestModel(test=test_models[0]),
            CapturedQueriesRelTestModel(test=test_models[0]),
        ])

        with catch_queries() as ctx:
            count = (
                CapturedQueriesTestModel.objects
                .filter(
                    Q(name__startswith='test') &
                    Exists(
                        CapturedQueriesRelTestModel.objects
                        .filter(
                            Q(test=OuterRef('pk')) &
                            ~Exists(
                                CapturedQueriesRelTestModel.objects
                                .filter(test=2)
                            )
                        )
                    )
                )
                .annotate(
                    sub1=Subquery(
                        CapturedQueriesRelTestModel.objects
                        .filter(
                            Q(test=OuterRef('pk')) &
                            Q(test__gt=Subquery(
                                CapturedQueriesRelTestModel.objects
                                .filter(test=OuterRef('pk'))
                                .annotate(some_value=Sum('pk') + 1)
                                .values('some_value')
                            ))
                        )
                        .values('pk')
                    ),
                )
                .distinct()
                .count()
            )

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        self._check_query(
            executed_queries[0],
            ctx=ctx,
            num_subqueries=1,
            sql=[
                'SELECT COUNT(*) FROM'
                ' (SELECT DISTINCT'
                '  "djblets_db_capturedqueriestestmodel"."id" AS "col1",'
                '  "djblets_db_capturedqueriestestmodel"."name" AS "col2",'
                '  "djblets_db_capturedqueriestestmodel"."flag" AS "col3",'
                '  (SELECT V0."id"'
                '    FROM "djblets_db_capturedqueriesreltestmodel" V0'
                '    WHERE (V0."test_id" ='
                '     ("djblets_db_capturedqueriestestmodel"."id") AND'
                '     V0."test_id" >'
                '     (SELECT (SUM(U0."id") + 1) AS "some_value"'
                '       FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '       WHERE U0."test_id" = (V0."id")'
                '       GROUP BY U0."id", U0."test_id"))) AS "sub1"'
                '  FROM "djblets_db_capturedqueriestestmodel"'
                '  WHERE'
                '   ("djblets_db_capturedqueriestestmodel"."name"'
                '     LIKE test% ESCAPE \'\\\' AND'
                '    EXISTS(SELECT 1 AS "a"'
                '     FROM "djblets_db_capturedqueriesreltestmodel" V0'
                '     WHERE'
                '      (V0."test_id" ='
                '       ("djblets_db_capturedqueriestestmodel"."id")'
                '       AND NOT EXISTS(SELECT 1 AS "a"'
                '        FROM "djblets_db_capturedqueriesreltestmodel" U0'
                '        WHERE U0."test_id" = 2'
                '        LIMIT 1))'
                '     LIMIT 1))) subquery',
            ])

        # Check the distinct subquery.
        distinct_subquery = executed_queries[0]['subqueries'][0]

        self._check_subquery(distinct_subquery,
                             ctx=ctx,
                             subquery_class=AggregateQuery,
                             num_subqueries=2,
                             can_compare_q=False)

        subqueries = distinct_subquery['subqueries']

        # Check annotate subquery 1.
        self._check_subquery(subqueries[0],
                             ctx=ctx,
                             subquery_class=Subquery,
                             num_subqueries=1,
                             can_compare_q=False)  # Subquery() again.
        self._check_subquery(subqueries[0]['subqueries'][0],
                             ctx=ctx,
                             subquery_class=Subquery,
                             can_compare_q=False)  # Subquery() again.

        # Check filter subquery 1.
        self._check_subquery(subqueries[1],
                             ctx=ctx,
                             subquery_class=Exists,
                             num_subqueries=1,
                             can_compare_q=False)   # Exists() again.
        self._check_subquery(subqueries[1]['subqueries'][0],
                             subquery_class=Exists,
                             ctx=ctx,
                             q=Q(test=2))

        # Check the fetched count.
        self.assertEqual(count, 1)

    def _check_query(
        self,
        executed_query: ExecutedQueryInfo,
        *,
        ctx: CatchQueriesContext,
        sql: List[str],
        num_subqueries: int = 0,
        query_type: ExecutedQueryType = ExecutedQueryType.SELECT,
        q: Optional[Q] = None,
        can_compare_q: bool = True,
    ) -> None:
        """Check the recorded information on a query.

        This will perform stanadrd checks on query state, and compare the
        provided attributes.

        Args:
            executed_query (dict):
                Information on the query that was executed.

            ctx (dict):
                The context information from catching the queries.

            sql (list of str):
                The expected list of SQL statements for the query.

            num_subqueries (int, optional):
                The expected number of subqueries within this query.

            query_type (djblets.db.query_catcher.ExecutedQueryType, optional):
                The expected query type.

                This defaults to ``SELECT`` queries.

            q (django.db.models.Q, optional):
                The Q object for the query, if any.

                This can be omitted if passing ``can_compare_q=False`` or
                for queries that lack filtering.

            can_compare_q (bool, optional):
                Whether ``q`` can be compared.

                If ``False``, this will merely check for the presence of a
                recorded Q object.

        Raises:
            AssertionError:
                One or more checks failed.
        """
        self.assertEqual(executed_query['result_type'], 'query')
        self.assertEqual(executed_query['type'], query_type)
        self._assert_sql(executed_query['sql'], sql)
        self.assertEqual(len(executed_query['subqueries']), num_subqueries)
        self.assertGreaterEqual(len(executed_query['traceback']), 1)

        query = executed_query['query']
        self.assertIsNotNone(query)

        if q is None and can_compare_q:
            self.assertNotIn(query, ctx.queries_to_qs)
        else:
            self.assertIn(query, ctx.queries_to_qs)

            if can_compare_q:
                self.assertEqual(ctx.queries_to_qs[query], q)

    def _check_subquery(
        self,
        executed_subquery: ExecutedSubQueryInfo,
        *,
        ctx: CatchQueriesContext,
        subquery_class: Type[Any],
        num_subqueries: int = 0,
        q: Optional[Q] = None,
        can_compare_q: bool = True,
    ) -> None:
        """Check the recorded information on a subquery.

        This will perform stanadrd checks on subquery state, and compare the
        provided attributes.

        Args:
            executed_subquery (dict):
                Information on the subquery that was executed.

            ctx (dict):
                The context information from catching the queries.

            subquery_class (type):
                The expected class for the subquery.

            num_subqueries (int, optional):
                The expected number of subqueries within this subquery.

            q (django.db.models.Q, optional):
                The Q object for the subquery, if any.

                This can be omitted if passing ``can_compare_q=False`` or
                for queries that lack filtering.

            can_compare_q (bool, optional):
                Whether ``q`` can be compared.

                If ``False``, this will merely check for the presence of a
                recorded Q object.

        Raises:
            AssertionError:
                One or more checks failed.
        """
        self.assertEqual(executed_subquery['result_type'], 'subquery')
        self.assertEqual(executed_subquery['type'], ExecutedQueryType.SELECT)
        self.assertIs(executed_subquery['cls'], subquery_class)
        self.assertEqual(len(executed_subquery['subqueries']), num_subqueries)

        query = executed_subquery['query']
        self.assertIsNotNone(query)

        if q is None and can_compare_q:
            self.assertNotIn(query, ctx.queries_to_qs)
        else:
            self.assertIn(query, ctx.queries_to_qs)

            if can_compare_q:
                self.assertEqual(ctx.queries_to_qs[query], q)

    def _assert_sql(
        self,
        sql1: List[str],
        sql2: List[str],
    ) -> None:
        """Assert that two lists of SQL statements are equal.

        This will normalize the lists, removing any extra whitespace that may
        be added to help format the SQL for editing and display.

        Args:
            sql1 (list of str):
                The first list of SQL statements.

            sql1 (list of str):
                The second list of SQL statements.

        Raises:
            AssertionError:
                The SQL statements are not equal.
        """
        extra_ws_re = self._extra_ws_re
        self.assertEqual(
            '\n'.join(
                extra_ws_re.sub(' ', _line)
                for _line in sql1
            ),
            '\n'.join(
                extra_ws_re.sub(' ', _line)
                for _line in sql2
            ))
