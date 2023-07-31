"""Unit tests for djblets.util.functional.

Version Added:
    4.0
"""

from __future__ import annotations

import re

import kgb

from djblets.testing.testcases import TestCase
from djblets.util.functional import iterable_len, lazy_re_compile


class IterableLenTests(TestCase):
    """Unit tests for iterable_len.

    Version Added:
        4.0
    """

    def test_with_len(self) -> None:
        """Testing iterable_len with iterable containing __len__"""
        self.assertEqual(iterable_len([1, 2, 3, 4, 5]), 5)

    def test_with_generator(self) -> None:
        """Testing iterable_len with generator"""
        gen = (
            i
            for i in range(5)
        )
        self.assertEqual(iterable_len(gen), 5)


class LazyReCompileTests(kgb.SpyAgency, TestCase):
    """Unit tests for lazy_re_compile.

    Version Added:
        4.0
    """

    def test_with_bytes(self) -> None:
        """Testing lazy_re_compile with byte string"""
        self.spy_on(re.compile)

        regex = lazy_re_compile(br'x\d+x', re.I)
        self.assertSpyNotCalled(re.compile)

        self.assertIsNotNone(regex.match(b'X123x'))
        self.assertSpyCallCount(re.compile, 1)

        self.assertIsNotNone(regex.match(b'X123x'))
        self.assertSpyCallCount(re.compile, 1)

    def test_with_str(self) -> None:
        """Testing lazy_re_compile with Unicode string"""
        self.spy_on(re.compile)

        regex = lazy_re_compile(r'x\d+x', re.I)
        self.assertSpyNotCalled(re.compile)

        self.assertIsNotNone(regex.match('X123x'))
        self.assertSpyCallCount(re.compile, 1)

        self.assertIsNotNone(regex.match('X123x'))
        self.assertSpyCallCount(re.compile, 1)
