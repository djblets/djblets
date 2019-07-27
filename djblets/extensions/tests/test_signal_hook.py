"""Unit tests for djblets.extensions.hooks.SignalHook."""

from __future__ import unicode_literals

from django.dispatch import Signal
from kgb import SpyAgency

from djblets.extensions.extension import Extension
from djblets.extensions.hooks import SignalHook
from djblets.extensions.tests.base import ExtensionTestsMixin
from djblets.testing.testcases import TestCase


class TestExtension(Extension):
    pass


class SignalHookTests(SpyAgency, ExtensionTestsMixin, TestCase):
    """Unit tests for djblets.extensions.hooks.SignalHook."""

    def setUp(self):
        super(SignalHookTests, self).setUp()

        self.test_extension = self.setup_extension(TestExtension)

        self.signal = Signal()
        self.spy_on(self._on_signal_fired)
        self.spy_on(self._on_signal_exception)

    def test_initialize(self):
        """Testing SignalHook initialization connects to signal"""
        SignalHook(self.test_extension, self.signal, self._on_signal_fired)

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 1)

    def test_shutdown(self):
        """Testing SignalHook.shutdown disconnects from signal"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired)
        hook.disable_hook()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_shutdown_with_sender(self):
        """Testing SignalHook.shutdown disconnects when a sender was set"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired, sender=self)
        hook.disable_hook()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_forwards_args(self):
        """Testing SignalHook forwards arguments to callback"""
        seen_kwargs = {}

        def callback(**kwargs):
            seen_kwargs.update(kwargs)

        SignalHook(self.test_extension, self.signal, callback)
        self.signal.send(sender=self, foo=1, bar=2)

        self.assertTrue('foo', seen_kwargs)
        self.assertEqual(seen_kwargs['foo'], 1)
        self.assertTrue('bar', seen_kwargs)
        self.assertEqual(seen_kwargs['bar'], 2)

    def test_sandbox_errors_true(self):
        """Testing SignalHook with sandbox_errors set to True logs errors"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=True)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def test_sandbox_errors_false(self):
        """Testing SignalHook with sandbox_errors set to False"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=False)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.assertRaises(Exception, self.signal.send, self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def _on_signal_fired(self, *args, **kwargs):
        pass

    def _on_signal_exception(self, *args, **kwargs):
        raise Exception
