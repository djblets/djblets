from __future__ import unicode_literals

from django.core import mail
from django.utils.datastructures import MultiValueDict
from kgb import SpyAgency

from djblets.mail.message import EmailMessage
from djblets.testing.testcases import TestCase


_CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class EmailTests(SpyAgency, TestCase):
    """Tests for sending e-mails."""

    def setUp(self):
        super(EmailTests, self).setUp()

        mail.outbox = []

    def test_headers_from_sender(self):
        """Testing EmailMessage From/Sender headers"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')
        self.assertEqual(email._headers['Sender'], 'noreply@example.com')
        self.assertEqual(email._headers['X-Sender'], 'noreply@example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Sender'], 'noreply@example.com')
        self.assertEqual(msg['X-Sender'], 'noreply@example.com')

    def test_extra_headers_dict(self):
        """Testing sending extra headers as a dict with an e-mail message"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             headers={
                                 'X-Foo': 'Bar',
                             })

        email.send()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-Foo', message._headers)
        self.assertEqual(message._headers['X-Foo'], 'Bar')

    def test_extra_headers_multivalue_dict(self):
        """Testing sending extra headers as a MultiValueDict with an e-mail
        message
        """
        header_values = ['Bar', 'Baz']

        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             headers=MultiValueDict({
                                 'X-Foo': header_values,
                             }))

        email.send()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertIn('X-Foo', message._headers)
        self.assertEqual(set(message._headers.getlist('X-Foo')),
                         set(header_values))

    def test_send_email_unicode_subject(self):
        """Testing sending an EmailMessage with a unicode subject"""
        email = EmailMessage(subject='\ud83d\ude04',
                             text_body='This is a test',
                             html_body='<p>This is a test</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        with self.settings(EMAIL_BACKEND=_CONSOLE_EMAIL_BACKEND):
            email.send()

    def test_send_email_unicode_body(self):
        """Testing sending an EmailMessage with a unicode body"""
        email = EmailMessage(subject='Test email',
                             text_body='\ud83d\ude04',
                             html_body='<p>\ud83d\ude04</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        # If the e-mail doesn't send correctly, it will raise a
        # UnicodeDecodeError.
        with self.settings(EMAIL_BACKEND=_CONSOLE_EMAIL_BACKEND):
            email.send()
