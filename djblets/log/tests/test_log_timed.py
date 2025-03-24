"""Unit tests for djblets.log.log_timed.

Version Added:
    5.3
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from django.http import HttpRequest

from djblets.log import log_timed
from djblets.testing.testcases import TestCase


root_logger = logging.getLogger()
test_logger = logging.getLogger(__name__)


class LogTimedTests(TestCase):
    """Unit tests for log_timed.

    Version Added:
        5.3
    """

    def test_as_func(self) -> None:
        """Testing log_timed as function"""
        with self._check_logs():
            t = log_timed('Doing a thing')
            t.done()

    def test_as_context_manager(self) -> None:
        """Testing log_timed as context manager"""
        with self._check_logs():
            with log_timed('Doing a thing'):
                pass

    def test_as_context_manager_and_exception(self) -> None:
        """Testing log_timed as context manager with an exception"""
        with self.assertRaisesMessage(Exception, 'oh no'):
            with self._check_logs():
                with log_timed('Doing a thing'):
                    raise Exception('oh no')

    def test_with_warning(self) -> None:
        """Testing log_timed with warning"""
        with self._check_logs(result_level_name='WARNING'):
            t = log_timed('Doing a thing',
                          warning_at=0.005)
            time.sleep(0.01)
            t.done()

    def test_with_critical(self) -> None:
        """Testing log_timed with critical"""
        with self._check_logs(result_level_name='CRITICAL'):
            t = log_timed('Doing a thing',
                          warning_at=0.002,
                          critical_at=0.005)
            time.sleep(0.01)
            t.done()

    def test_with_default_level(self) -> None:
        """Testing log_timed with default_level"""
        with self._check_logs(default_level_name='INFO',
                              result_level_name='INFO'):
            t = log_timed('Doing a thing',
                          default_level=logging.INFO)
            t.done()

    def test_with_extra(self) -> None:
        """Testing log_timed with extra="""
        with self._check_logs() as cm:
            t = log_timed(
                'Doing a thing',
                extra={
                    'foo': 'bar',
                })
            t.done()

        for record in cm.records:
            self.assertEqual(record.foo, 'bar')
            self.assertIsNone(record.request)

    def test_with_extra_and_request(self) -> None:
        """Testing log_timed with extra= and request="""
        request = HttpRequest()

        with self._check_logs() as cm:
            t = log_timed(
                'Doing a thing',
                extra={
                    'foo': 'bar',
                },
                request=request)
            t.done()

        for record in cm.records:
            self.assertEqual(record.foo, 'bar')
            self.assertIs(record.request, request)

    def test_with_logger(self) -> None:
        """Testing log_timed with logger"""
        with self._check_logs(logger_name=__name__):
            t = log_timed('Doing a thing',
                          logger=test_logger)
            t.done()

    def test_with_request(self) -> None:
        """Testing log_timed with request"""
        request = HttpRequest()

        with self._check_logs() as cm:
            t = log_timed('Doing a thing',
                          request=request)
            t.done()

        for record in cm.records:
            self.assertIs(record.request, request)

    @contextmanager
    def _check_logs(
        self,
        *,
        logger_name: str = 'root',
        default_level_name: str = 'DEBUG',
        result_level_name: str = 'DEBUG',
    ) -> Iterator[Any]:
        """Capture timed logs and run tests.

        This will capture any logs for the unit test and then check that the
        log output meets the provided criteria.

        Args:
            logger_name (str, optional):
                The name of the logger to expect in results.

            default_level_name (str, optional):
                The name of the level to expect in the begin/end log lines.

            result_level_name (str, optional):
                The name of the level to expect in the timing result log line.

        Context:
            object:
            The log assertion context for further checks.
        """
        with self.assertLogs(level=logging.DEBUG) as cm:
            yield cm

        assert cm.records[2].args

        trace_id, seconds, microseconds = cm.records[2].args

        self.assertIs(trace_id, cm.records[2].trace_id)
        self.assertIsInstance(seconds, int)
        self.assertIsInstance(microseconds, int)

        self.assertEqual(cm.output, [
            f'{default_level_name}:{logger_name}:[{trace_id}] Begin: '
            f'Doing a thing',

            f'{default_level_name}:{logger_name}:[{trace_id}] End: Doing a '
            f'thing',

            f'{result_level_name}:{logger_name}:[{trace_id}] Doing a thing '
            f'took {seconds}.{microseconds:06d} seconds',
        ])
