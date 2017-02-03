from __future__ import unicode_literals

from django.db import connection

from djblets.testing.testcases import TestCase


class CursorDebugWrapperTests(TestCase):
    """Unit tests for djblets.log.middleware.CursorDebugWrapper."""

    def test_execute(self):
        """Testing CursorDebugWrapper.execute"""
        with self.assertNumQueries(1):
            connection.cursor().execute(
                'INSERT INTO django_site (name, domain) VALUES (%s, %s)',
                ('site1', 'domain1.com'))

        self.assertIn('stack', self._get_queries()[-1])

    def test_executemany(self):
        """Testing CursorDebugWrapper.executemany"""
        with self.assertNumQueries(1):
            connection.cursor().executemany(
                'INSERT INTO django_site (name, domain) VALUES (%s, %s)',
                [
                    ('site1', 'domain1.com'),
                    ('site2', 'domain2.com'),
                ])

        self.assertIn('stack', self._get_queries()[-1])

    def _get_queries(self):
        try:
            # Django >+ 1.8
            return connection.queries_log
        except AttributeError:
            # Django < 1.8
            return connection.queries
