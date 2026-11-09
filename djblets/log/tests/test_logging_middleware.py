"""Unit tests for djblets.log.middleware.LoggingMiddleware.

Version Added:
    6.1.1
"""

from __future__ import annotations

import logging
import sys

import kgb
from django.contrib.auth.models import AnonymousUser, User
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from djblets.log import init_logging
from djblets.log.middleware import LoggingMiddleware
from djblets.testing.testcases import TestCase


# Workaround for different implementations of assertNoLogs() between Django and
# the standard library.
if sys.version_info < (3, 10):
    root_logger = 'root'
else:
    root_logger = None


def _view(
    request: HttpRequest,
) -> HttpResponse:
    """Return a basic response for the test view.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        django.http.HttpResponse:
        The response.
    """
    # Perform some database query.
    User.objects.count()

    return HttpResponse('yay')


@override_settings(DEBUG=False)
class LoggingMiddlewareTests(kgb.SpyAgency, TestCase):
    """Unit tests for LoggingMiddleware.

    Version Added:
        6.1.1
    """

    ######################
    # Instance variables #
    ######################

    #: The middleware being tested.
    middleware: LoggingMiddleware

    def setUp(self) -> None:
        """Set up state for the test.

        This will construct the middleware to execute.
        """
        super().setUp()

        self.middleware = LoggingMiddleware(get_response=_view)

    def tearDown(self) -> None:
        """Tear down state for the test.

        This will restore state on the connection if anything changed it.
        """
        connection.force_debug_cursor = False

        super().tearDown()

    def test_with_defaults(self) -> None:
        """Testing LoggingMiddleware with defaults"""
        self.spy_on(init_logging)

        self._run_request('/')

        self.assertSpyCalledOnce(init_logging)

    @override_settings(LOGGING_PAGE_TIMES=True)
    def test_with_page_times(self) -> None:
        """Testing LoggingMiddleware with LOGGING_PAGE_TIMES=True"""
        with self.assertLogs(level=logging.DEBUG) as logs:
            self._run_request(
                '/',
                expect_timed_logs=True,
            )

        self.assertEqual(len(logs.output), 3)
        self.assertRegex(
            logs.output[0],
            r'DEBUG:root:\[.+\] Begin: Page request: HTTP GET / \(by '
            r'AnonymousUser\)',
        )
        self.assertRegex(
            logs.output[1],
            r'DEBUG:root:\[.+\] End: Page request: HTTP GET / \(by '
            r'AnonymousUser\)',
        )
        self.assertRegex(
            logs.output[2],
            r'DEBUG:root:\[.+\] Page request: HTTP GET / \(by '
            r'AnonymousUser\) took \d+\.\d+ seconds',
        )

    @override_settings(LOGGING_ALLOW_PROFILING=True)
    def test_with_profiling_and_allowed(self) -> None:
        """Testing LoggingMiddleware with ?profiling=1 and
        LOGGING_ALLOW_PROFILING=True
        """
        with self.assertLogs() as logs:
            self._run_request(
                '/?profiling=1',
                expect_force_debug_cursor=True,
                expect_profiler=True,
            )

        self.assertEqual(len(logs.output), 4)
        self.assertEqual(
            logs.output[0],
            'INFO:profile:Profiling results for / (HTTP GET):',
        )
        self.assertRegex(
            logs.output[1],
            r'INFO:profile:\d+ function calls \(\d+ primitive calls\) in '
            r'\d+.\d+ seconds\n\n.+',
        )
        self.assertEqual(
            logs.output[2],
            'INFO:profile:1 database queries made\n'
        )
        self.assertRegex(
            logs.output[3],
            r'INFO:profile:SQL Query profile .+',
        )

    @override_settings(LOGGING_ALLOW_PROFILING=False)
    def test_with_profiling_and_not_allowed(self) -> None:
        """Testing LoggingMiddleware with ?profiling=1 and
        LOGGING_ALLOW_PROFILING=False
        """
        with self.assertNoLogs(logger=root_logger):
            self._run_request('/?profiling=1')

    @override_settings(LOGGING_ALLOW_PROFILING=True)
    def test_with_no_profiling_and_allowed(self) -> None:
        """Testing LoggingMiddleware with no ?profiling and
        LOGGING_ALLOW_PROFILING=True
        """
        with self.assertNoLogs(logger=root_logger):
            self._run_request('/')

    def _run_request(
        self,
        url: str,
        *,
        expect_force_debug_cursor: bool = False,
        expect_profiler: bool = False,
        expect_timed_logs: bool = False,
    ) -> HttpRequest:
        """Run a request through the logging middleware.

        Args:
            url (str):
                The URL to request.

            expect_force_debug_cursor (bool, optional):
                Whether it's expected that a debug cursor will be forced
                during the request.

            expect_profiler (bool, optional):
                Whether a profiler was expected to be created.

            expect_timed_logs (bool, optional):
                Whether timed logs was expected to be set up.

        Returns:
            django.http.HttpRequest:
            The request that was processed.
        """
        middleware = self.middleware
        request = RequestFactory().get(url)
        request.user = AnonymousUser()

        middleware.process_request(request)

        self.assertEqual(connection.force_debug_cursor,
                         expect_force_debug_cursor)

        response = middleware.process_view(request, _view, (), {})

        if response is None:
            response = _view(request)

        middleware.process_response(request, response)

        self.assertFalse(connection.force_debug_cursor)

        profiler = getattr(request, '_djblets_profiler', None)
        timed_log_info = getattr(request, '_djblets_page_timedloginfo', None)

        if expect_profiler:
            self.assertIsNotNone(profiler)
        else:
            self.assertIsNone(profiler)

        if expect_timed_logs:
            self.assertIsNotNone(timed_log_info)
        else:
            self.assertIsNone(timed_log_info)

        return request
