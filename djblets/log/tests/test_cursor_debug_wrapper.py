from importlib import import_module

from django.db import connection

from djblets.testing.testcases import TestCase


# We need to ensure that the following module is imported so that the debug
# wrapper is replaced with our own.
import_module('djblets.log.middleware')


class CursorDebugWrapperTests(TestCase):
    """Unit tests for djblets.log.middleware.CursorDebugWrapper."""

    def test_execute(self):
        """Testing CursorDebugWrapper.execute"""
        with self.assertNumQueries(1):
            connection.cursor().execute(
                'INSERT INTO django_site (name, domain) VALUES (%s, %s)',
                ('site1', 'domain1.com'))

        self.assertIn('stack', connection.queries_log[-1])

    def test_executemany(self):
        """Testing CursorDebugWrapper.executemany"""
        with self.assertNumQueries(1):
            connection.cursor().executemany(
                'INSERT INTO django_site (name, domain) VALUES (%s, %s)',
                [
                    ('site1', 'domain1.com'),
                    ('site2', 'domain2.com'),
                ])

        self.assertIn('stack', connection.queries_log[-1])
