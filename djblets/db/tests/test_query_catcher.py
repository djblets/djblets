"""Unit tests for djblets.db.query_catcher.

Version Added:
    3.4
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from djblets.db.query_catcher import (ExecutedQueryType,
                                      catch_queries)
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class CapturedQueriesTestModel(models.Model):
    name = models.CharField(max_length=10)
    flag = models.BooleanField(default=True)


class CaptureQueriesTests(TestModelsLoaderMixin, TestCase):
    """Unit tests for djblets.db.query_catcher.catch_queries.

    Version Added:
        3.4
    """

    tests_app = 'djblets.db.tests'

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

        executed_query = executed_queries[0]
        self.assertEqual(executed_query['type'], ExecutedQueryType.SELECT)
        self.assertEqual(
            executed_query['sql'],
            [
                'SELECT "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE ("djblets_db_capturedqueriestestmodel"."name"'
                ' LIKE test% ESCAPE \'\\\' AND'
                ' "djblets_db_capturedqueriestestmodel"."flag")',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)

        query = executed_query['query']
        self.assertIsNotNone(query)

        self.assertEqual(ctx.queries_to_qs.get(query),
                         Q(Q(name__startswith='test') &
                           Q(flag=True)))

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

        executed_query = executed_queries[0]
        self.assertEqual(executed_query['type'], ExecutedQueryType.INSERT)
        self.assertEqual(
            executed_query['sql'],
            [
                'INSERT INTO "djblets_db_capturedqueriestestmodel"'
                ' ("name", "flag")'
                ' SELECT test1, True UNION ALL SELECT test2, True',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)

        query = executed_query['query']
        self.assertIsNotNone(query)
        self.assertIsNone(ctx.queries_to_qs.get(query))

    def test_with_delete(self) -> None:
        """Testing capture_queries with DELETE"""
        obj = CapturedQueriesTestModel.objects.create(name='test')
        obj_id = obj.pk

        with catch_queries() as ctx:
            obj.delete()

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        executed_query = executed_queries[0]
        self.assertEqual(executed_query['type'], ExecutedQueryType.DELETE)
        self.assertEqual(
            executed_query['sql'],
            [
                'DELETE FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" IN (1)',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)

        query = executed_query['query']
        self.assertIsNotNone(query)
        self.assertEqual(ctx.queries_to_qs.get(query),
                         Q(id__in=[obj_id]))

    def test_with_update(self) -> None:
        """Testing capture_queries with UPDATE"""
        obj = CapturedQueriesTestModel.objects.create(name='test')

        with catch_queries() as ctx:
            obj.flag = False
            obj.save(update_fields=('flag',))

        executed_queries = ctx.executed_queries
        self.assertEqual(len(executed_queries), 1)

        executed_query = executed_queries[0]
        self.assertEqual(executed_query['type'], ExecutedQueryType.UPDATE)
        self.assertEqual(
            executed_query['sql'],
            [
                'UPDATE "djblets_db_capturedqueriestestmodel"'
                ' SET "flag" = False'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" = 1',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)

        query = executed_query['query']
        self.assertIsNotNone(query)
        self.assertEqual(ctx.queries_to_qs.get(query),
                         Q(pk=obj.pk))

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

        executed_query = executed_queries[0]
        self.assertEqual(executed_query['type'], ExecutedQueryType.INSERT)
        self.assertEqual(
            executed_query['sql'],
            [
                'INSERT INTO "djblets_db_capturedqueriestestmodel"'
                ' ("name", "flag")'
                ' SELECT test, True',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)
        self.assertIsNone(ctx.queries_to_qs.get(executed_query['query']))

        executed_query = executed_queries[1]
        self.assertEqual(executed_query['type'], ExecutedQueryType.UPDATE)
        self.assertEqual(
            executed_query['sql'],
            [
                'UPDATE "djblets_db_capturedqueriestestmodel"'
                ' SET "flag" = False'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" = 1',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)
        self.assertEqual(ctx.queries_to_qs.get(executed_query['query']),
                         Q(pk=1))

        executed_query = executed_queries[2]
        self.assertEqual(executed_query['type'], ExecutedQueryType.SELECT)
        self.assertEqual(
            executed_query['sql'],
            [
                'SELECT "djblets_db_capturedqueriestestmodel"."id",'
                ' "djblets_db_capturedqueriestestmodel"."name",'
                ' "djblets_db_capturedqueriestestmodel"."flag"'
                ' FROM "djblets_db_capturedqueriestestmodel"',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)
        self.assertIsNone(ctx.queries_to_qs.get(executed_query['query']))

        executed_query = executed_queries[3]
        self.assertEqual(executed_query['type'], ExecutedQueryType.DELETE)
        self.assertEqual(
            executed_query['sql'],
            [
                'DELETE FROM "djblets_db_capturedqueriestestmodel"'
                ' WHERE "djblets_db_capturedqueriestestmodel"."id" IN (1)',
            ])
        self.assertGreaterEqual(len(executed_query['traceback']), 1)
        self.assertEqual(ctx.queries_to_qs.get(executed_query['query']),
                         Q(id__in=[1]))
