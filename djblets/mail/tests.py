"""Unit tests for djblets.mail."""

import dns.resolver
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test.utils import override_settings
from django.utils.datastructures import MultiValueDict

from djblets.deprecation import RemovedInDjblets60Warning
from djblets.mail.dmarc import (DmarcPolicy, get_dmarc_record,
                                is_email_allowed_by_dmarc)
from djblets.mail.message import EmailMessage
from djblets.mail.testing import DmarcDnsTestsMixin
from djblets.mail.utils import (build_email_address,
                                build_email_address_for_user,
                                build_email_address_via_service)
from djblets.testing.testcases import TestCase


_CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class DmarcTests(DmarcDnsTestsMixin, TestCase):
    """Tests for DMARC support."""

    def test_get_dmarc_record_with_no_record(self):
        """Testing get_dmarc_record with no DMARC record in DNS"""
        self.assertIsNone(get_dmarc_record('example.com', use_cache=False))

    def test_get_dmarc_record_with_empty(self):
        """Testing get_dmarc_record with empty DMARC record in DNS"""
        self.dmarc_txt_records['_dmarc.example.com'] = ''
        self.assertIsNone(get_dmarc_record('example.com', use_cache=False))

    def test_get_dmarc_record_with_org_domain(self):
        """Testing get_dmarc_record with falling back to organizational
        domain
        """
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1; p=reject;'

        record = get_dmarc_record('mail.corp.example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.REJECT)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'reject',
            })

    def test_get_dmarc_record_with_version_only(self):
        """Testing get_dmarc_record with DMARC record containing a DMARC
        version only
        """
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.UNSET)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 100)
        self.assertEqual(record.fields, {'v': 'DMARC1'})

    def test_get_dmarc_record_with_p_none(self):
        """Testing get_dmarc_record with DMARC record with p=none"""
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1; p=none;'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.NONE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'none',
            })

    def test_get_dmarc_record_with_p_quarantine(self):
        """Testing get_dmarc_record with DMARC record with p=quarantine"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine; pct=20'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 20)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'pct': '20',
            })

    def test_get_dmarc_record_with_p_reject(self):
        """Testing get_dmarc_record with DMARC record with p=reject"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=reject; pct=100'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.REJECT)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'reject',
                'pct': '100',
            })

    def test_get_dmarc_record_with_sp_none(self):
        """Testing get_dmarc_record with DMARC record with sp=none"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine; sp=none;'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.NONE)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'sp': 'none',
            })

    def test_get_dmarc_record_with_sp_quarantine(self):
        """Testing get_dmarc_record with DMARC record with sp=quarantine"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine; sp=quarantine;'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'sp': 'quarantine',
            })

    def test_get_dmarc_record_with_sp_reject(self):
        """Testing get_dmarc_record with DMARC record with p=reject"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine; sp=reject;'

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.REJECT)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'sp': 'reject',
            })

    def test_get_dmarc_record_with_multiple_strings(self) -> None:
        """Testing get_dmarc_record with DMARC record with multiple strings"""
        self.dmarc_txt_records['_dmarc.example.com'] = [
            'v=DMARC1;',
            'p=quarantine;',
            'pct=20',
        ]

        record = get_dmarc_record('example.com', use_cache=False)
        assert record

        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 20)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'pct': '20',
            })

    def test_get_dmarc_record_with_different_whitespace(self):
        """Testing get_dmarc_record with DMARC record with different amounts
        of whitespace in record
        """
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1;p=quarantine;  sp = reject; '

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.REJECT)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'sp': 'reject',
            })

    def test_get_dmarc_record_with_bad_format(self):
        """Testing get_dmarc_record with DMARC record with bad format issues"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine; ; =value; a=b=c; sp='

        record = get_dmarc_record('example.com', use_cache=False)
        self.assertIsNotNone(record)
        self.assertEqual(record.hostname, 'example.com')
        self.assertEqual(record.policy, DmarcPolicy.QUARANTINE)
        self.assertEqual(record.subdomain_policy, DmarcPolicy.UNSET)
        self.assertEqual(record.pct, 100)
        self.assertEqual(
            record.fields,
            {
                'v': 'DMARC1',
                'p': 'quarantine',
                'a': 'b=c',
            })

    def test_get_dmarc_record_with_cache(self):
        """Testing get_dmarc_record with use_cache=True"""
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1; p=reject;'

        record1 = get_dmarc_record('example.com', use_cache=True)
        self.assertIsNotNone(record1)
        self.assertEqual(record1.hostname, 'example.com')
        self.assertEqual(
            record1.fields,
            {
                'v': 'DMARC1',
                'p': 'reject',
            })

        record2 = get_dmarc_record('example.com', use_cache=True)
        self.assertEqual(record1, record2)

        self.assertEqual(len(dns.resolver.resolve.spy.calls), 1)

    def test_is_email_allowed_by_dmarc_with_domain_policy_none(self):
        """Testing is_email_allowed_by_dmarc with domain policy=none"""
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1; p=none;'
        self.assertTrue(is_email_allowed_by_dmarc('test@example.com'))

    def test_is_email_allowed_by_dmarc_with_domain_policy_quarantine(self):
        """Testing is_email_allowed_by_dmarc with domain policy=quarantine"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=quarantine;'
        self.assertFalse(is_email_allowed_by_dmarc('test@example.com'))

    def test_is_email_allowed_by_dmarc_with_domain_policy_reject(self):
        """Testing is_email_allowed_by_dmarc with domain policy=reject"""
        self.dmarc_txt_records['_dmarc.example.com'] = 'v=DMARC1; p=reject;'
        self.assertFalse(is_email_allowed_by_dmarc('test@example.com'))

    def test_is_email_allowed_by_dmarc_with_domain_policy_pct_0(self):
        """Testing is_email_allowed_by_dmarc with domain 0% match"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=reject; pct=0;'
        self.assertTrue(is_email_allowed_by_dmarc('test@example.com'))

    def test_is_email_allowed_by_dmarc_with_subdomain_policy_none(self):
        """Testing is_email_allowed_by_dmarc with subdomain and policy=none"""
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=reject; sp=none;'
        self.assertTrue(is_email_allowed_by_dmarc('test@mail.example.com'))

    def test_is_email_allowed_by_dmarc_with_subdomain_policy_quarantine(self):
        """Testing is_email_allowed_by_dmarc with subdomain and
        policy=quarantine
        """
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=reject; sp=quarantine;'
        self.assertFalse(is_email_allowed_by_dmarc('test@mail.example.com'))

    def test_is_email_allowed_by_dmarc_with_subdomain_policy_reject(self):
        """Testing is_email_allowed_by_dmarc with subdomain and policy=reject
        """
        self.dmarc_txt_records['_dmarc.example.com'] = \
            'v=DMARC1; p=reject; sp=reject;'
        self.assertFalse(is_email_allowed_by_dmarc('test@mail.example.com'))


class EmailMessageTests(DmarcDnsTestsMixin, TestCase):
    """Tests for djblets.mail.message.EmailMessage."""

    def setUp(self):
        super(EmailMessageTests, self).setUp()

        mail.outbox = []

    def test_init_with_text_body_as_unicode(self):
        """Testing EmailMessage.__init__ with text_body=<unicode>"""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body=b'This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertEqual(email.body, 'This is a test.')
        self.assertIsInstance(email.body, str)

    def test_init_with_text_body_as_bytes(self):
        """Testing EmailMessage.__init__ with text_body=<bytes>"""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body=b'This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertEqual(email.body, 'This is a test.')
        self.assertIsInstance(email.body, str)

    def test_init_with_html_body_as_unicode(self):
        """Testing EmailMessage.__init__ with html_body=<unicode>"""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertEqual(email.alternatives,
                         [('<p>This is a test.</p>', 'text/html')])
        self.assertIsInstance(email.alternatives[0][0], str)

    def test_init_with_html_body_as_bytes(self):
        """Testing EmailMessage.__init__ with html_body=<bytes>"""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body=b'<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertEqual(email.alternatives,
                         [('<p>This is a test.</p>', 'text/html')])
        self.assertIsInstance(email.alternatives[0][0], str)

    def test_message_with_from(self):
        """Testing EmailMessage.message with from_email="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc <doc@example.com>',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc <doc@example.com>'])
        self.assertEqual(email.extra_headers['From'], 'Doc <doc@example.com>')
        self.assertEqual(email._headers['Sender'], settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email._headers['X-Sender'],
                         settings.DEFAULT_FROM_EMAIL)

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc <doc@example.com>')
        self.assertEqual(msg['Reply-To'], 'Doc <doc@example.com>')

    def test_message_with_from_and_unicode(self):
        """Testing EmailMessage.message with from_email= with Unicode
        characters
        """
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Døc <doc@example.com>',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Døc <doc@example.com>'])
        self.assertEqual(email.extra_headers['From'], 'Døc <doc@example.com>')
        self.assertEqual(email._headers['Sender'], settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email._headers['X-Sender'],
                         settings.DEFAULT_FROM_EMAIL)

        msg = email.message()
        self.assertEqual(msg['From'], '=?utf-8?q?D=C3=B8c?= <doc@example.com>')
        self.assertEqual(msg['Reply-To'],
                         '=?utf-8?q?D=C3=B8c?= <doc@example.com>')

    def test_message_with_sender(self):
        """Testing EmailMessage.message with sender="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='Sender <noreply@example.com>',
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')
        self.assertEqual(email._headers['Sender'],
                         'Sender <noreply@example.com>')
        self.assertEqual(email._headers['X-Sender'],
                         'Sender <noreply@example.com>')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Sender'], 'Sender <noreply@example.com>')
        self.assertEqual(msg['X-Sender'], 'Sender <noreply@example.com>')

    def test_message_with_sender_with_unicode(self):
        """Testing EmailMessage.message with sender= with Unicode characters"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='Sénder <noreply@example.com>',
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')
        self.assertEqual(email._headers['Sender'],
                         'Sénder <noreply@example.com>')
        self.assertEqual(email._headers['X-Sender'],
                         'Sénder <noreply@example.com>')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Sender'],
                         '=?utf-8?q?S=C3=A9nder?= <noreply@example.com>')

        # Django specially handles several address-related headers, parsing
        # out the name from the e-mail address, in order to selectively
        # encode only the name. It does not know X-Sender, though, and will
        # encode the entire string.
        #
        # This shouldn't be a problem in practice (and we've been doing it
        # this way for years), but that's the reason this doesn't resemble
        # the value from 'Sender' above.
        self.assertEqual(
            msg['X-Sender'],
            '=?utf-8?b?U8OpbmRlciA8bm9yZXBseUBleGFtcGxlLmNvbT4=?=')

    def test_message_with_reply_to(self):
        """Testing EmailMessage.message with reply_to="""
        email = EmailMessage(
            subject='Test email',
            text_body='This is a test.',
            html_body='<p>This is a test.</p>',
            from_email='doc@example.com',
            to=['sleepy@example.com'],
            reply_to=[
                'User1 <user1@example.com>',
                'User2 <user2@example.com>',
            ],
            from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Reply-To', email.extra_headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, [
            'User1 <user1@example.com>',
            'User2 <user2@example.com>',
        ])
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Reply-To'],
                         'User1 <user1@example.com>, '
                         'User2 <user2@example.com>')

    def test_message_with_reply_to_with_unicode(self):
        """Testing EmailMessage.message with sender= with Unicode characters"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             reply_to=['Usér <user@example.com>'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Reply-To', email.extra_headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Usér <user@example.com>'])
        self.assertEqual(email.extra_headers['From'], 'doc@example.com')

        msg = email.message()
        self.assertEqual(msg['Reply-To'],
                         '=?utf-8?b?VXPDqXI=?= <user@example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_from_spoofing_always(self):
        """Testing EmailMessage.message with from_spoofing=always"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_ALWAYS)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'], 'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_from_spoofing_smart_and_allowed(self):
        """Testing EmailMessage.message with from_spoofing=smart and From
        address allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=none;'

        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_SMART)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'], 'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_from_spoofing_smart_and_not_allowed(self):
        """Testing EmailMessage.message with from_spoofing=smart and From
        address not allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=quarantine;'

        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_SMART)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_from_spoofing_never(self):
        """Testing EmailMessage.message with from_spoofing=never"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'],
                             from_spoofing=EmailMessage.FROM_SPOOFING_NEVER)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service',
                       DJBLETS_EMAIL_FROM_SPOOFING='always')
    def test_message_with_from_spoofing_setting_always(self):
        """Testing EmailMessage.message with
        settings.DJBLETS_EMAIL_FROM_SPOOFING=always
        """
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'], 'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service',
                       DJBLETS_EMAIL_FROM_SPOOFING='smart')
    def test_message_with_from_spoofing_setting_smart_and_allowed(self):
        """Testing EmailMessage.message with
        settings.DJBLETS_EMAIL_FROM_SPOOFING=smart and From address allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=none;'

        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'], 'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service',
                       DJBLETS_EMAIL_FROM_SPOOFING='smart')
    def test_message_with_from_spoofing_setting_smart_and_not_allowed(self):
        """Testing EmailMessage.message with
        settings.DJBLETS_EMAIL_FROM_SPOOFING=smart and From address not allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=quarantine;'

        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service',
                       DJBLETS_EMAIL_FROM_SPOOFING='never')
    def test_message_with_from_spoofing_setting_never(self):
        """Testing EmailMessage.message with
        settings.DJBLETS_EMAIL_FROM_SPOOFING=never
        """
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='Doc Dwarf <doc@corp.example.com>',
                             sender='noreply@mail.example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_enable_smart_spoofing_true_and_allowed(self):
        """Testing EmailMessage.message with enable_smart_spoofing=True and
        From address allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=none;'

        message = (
            'settings.EMAIL_ENABLE_SMART_SPOOFING and the '
            'enable_smart_spoofing argument to '
            'djblets.mail.message.MailMessage are deprecated, and will be '
            'removed in Djblets 6. Pleaase use '
            'settings.DJBLETS_EMAIL_FROM_SPOOFING and the from_spoofing= '
            'argument instead.'
        )

        with self.assertWarns(RemovedInDjblets60Warning, message):
            email = EmailMessage(subject='Test email',
                                 text_body='This is a test.',
                                 from_email='Doc Dwarf <doc@corp.example.com>',
                                 sender='noreply@mail.example.com',
                                 to=['sleepy@example.com'],
                                 enable_smart_spoofing=True)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_enable_smart_spoofing_true_and_not_allowed(self):
        """Testing EmailMessage.message with enable_smart_spoofing=True and
        From address not allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=quarantine;'

        message = (
            'settings.EMAIL_ENABLE_SMART_SPOOFING and the '
            'enable_smart_spoofing argument to '
            'djblets.mail.message.MailMessage are deprecated, and will be '
            'removed in Djblets 6. Pleaase use '
            'settings.DJBLETS_EMAIL_FROM_SPOOFING and the from_spoofing= '
            'argument instead.'
        )

        with self.assertWarns(RemovedInDjblets60Warning, message):
            email = EmailMessage(subject='Test email',
                                 text_body='This is a test.',
                                 from_email='Doc Dwarf <doc@corp.example.com>',
                                 sender='noreply@mail.example.com',
                                 to=['sleepy@example.com'],
                                 enable_smart_spoofing=True)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_message_with_enable_smart_spoofing_false(self):
        """Testing EmailMessage.message with enable_smart_spoofing=False"""
        message = (
            'settings.EMAIL_ENABLE_SMART_SPOOFING and the '
            'enable_smart_spoofing argument to '
            'djblets.mail.message.MailMessage are deprecated, and will be '
            'removed in Djblets 6. Pleaase use '
            'settings.DJBLETS_EMAIL_FROM_SPOOFING and the from_spoofing= '
            'argument instead.'
        )

        with self.assertWarns(RemovedInDjblets60Warning, message):
            email = EmailMessage(subject='Test email',
                                 text_body='This is a test.',
                                 from_email='Doc Dwarf <doc@corp.example.com>',
                                 sender='noreply@mail.example.com',
                                 to=['sleepy@example.com'],
                                 enable_smart_spoofing=False)

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'Doc Dwarf <doc@corp.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service',
                       EMAIL_ENABLE_SMART_SPOOFING=True)
    def test_message_with_smart_spoofing_setting_true_and_not_allowed(self):
        """Testing EmailMessage.message with
        settings.EMAIL_ENABLE_SMART_SPOOFING=True and
        From address not allowed
        """
        self.dmarc_txt_records['_dmarc.corp.example.com'] = \
            'v=DMARC1; p=quarantine;'

        message = (
            'settings.EMAIL_ENABLE_SMART_SPOOFING and the '
            'enable_smart_spoofing argument to '
            'djblets.mail.message.MailMessage are deprecated, and will be '
            'removed in Djblets 6. Pleaase use '
            'settings.DJBLETS_EMAIL_FROM_SPOOFING and the from_spoofing= '
            'argument instead.'
        )

        with self.assertWarns(RemovedInDjblets60Warning, message):
            email = EmailMessage(subject='Test email',
                                 text_body='This is a test.',
                                 from_email='Doc Dwarf <doc@corp.example.com>',
                                 sender='noreply@mail.example.com',
                                 to=['sleepy@example.com'])

        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertNotIn('Reply-To', email._headers)
        self.assertIn('From', email.extra_headers)
        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['Doc Dwarf <doc@corp.example.com>'])
        self.assertEqual(email.extra_headers['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(email._headers['Sender'],
                         'noreply@mail.example.com')
        self.assertEqual(email._headers['X-Sender'],
                         'noreply@mail.example.com')

        msg = email.message()
        self.assertEqual(msg['From'],
                         'Doc Dwarf via My Service <noreply@mail.example.com>')
        self.assertEqual(msg['Reply-To'],
                         'Doc Dwarf <doc@corp.example.com>')

    def test_message_with_in_reply_to(self):
        """Testing EmailMessage.message with in_reply_to="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             in_reply_to='Someone <someone@example.com>')

        self.assertIn('In-Reply-To', email._headers)
        self.assertIn('References', email._headers)
        self.assertEqual(email._headers['In-Reply-To'],
                         'Someone <someone@example.com>')
        self.assertEqual(email._headers['References'],
                         'Someone <someone@example.com>')

        msg = email.message()
        self.assertEqual(msg['In-Reply-To'], 'Someone <someone@example.com>')
        self.assertEqual(msg['References'], 'Someone <someone@example.com>')

    def test_message_with_in_reply_to_and_unicode(self):
        """Testing EmailMessage.message with in_reply_to= with Unicode
        characters
        """
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             in_reply_to='Sømeone <someone@example.com>')

        self.assertIn('In-Reply-To', email._headers)
        self.assertIn('References', email._headers)
        self.assertEqual(email._headers['In-Reply-To'],
                         'Sømeone <someone@example.com>')
        self.assertEqual(email._headers['References'],
                         'Sømeone <someone@example.com>')

        msg = email.message()
        self.assertEqual(
            msg['In-Reply-To'],
            '=?utf-8?b?U8O4bWVvbmUgPHNvbWVvbmVAZXhhbXBsZS5jb20+?=')
        self.assertEqual(
            msg['References'],
            '=?utf-8?b?U8O4bWVvbmUgPHNvbWVvbmVAZXhhbXBsZS5jb20+?=')

    def test_message_with_auto_generated_true(self):
        """Testing EmailMessage.message with auto_generated=True"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             auto_generated=True)

        self.assertIn('Auto-Submitted', email._headers)
        self.assertEqual(email._headers['Auto-Submitted'], 'auto-generated')

        msg = email.message()
        self.assertEqual(msg['Auto-Submitted'], 'auto-generated')

    def test_message_with_auto_generated_false(self):
        """Testing EmailMessage.message with auto_generated=False"""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('Auto-Submitted', email._headers)

        msg = email.message()
        self.assertNotIn('Auto-Submitted', msg)

    def test_message_with_prevent_auto_responses_true(self):
        """Testing EmailMessage.message with prevent_auto_responses=True"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             prevent_auto_responses=True)

        self.assertIn('X-Auto-Response-Suppress', email._headers)
        self.assertEqual(email._headers['X-Auto-Response-Suppress'],
                         'DR, RN, OOF, AutoReply')

        msg = email.message()
        self.assertEqual(msg['X-Auto-Response-Suppress'],
                         'DR, RN, OOF, AutoReply')

    def test_message_with_prevent_auto_responses_false(self):
        """Testing EmailMessage.message with prevent_auto_responses=False"""
        # prevent_auto_responses is False by default, so test with that case
        # to ensure it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('X-Auto-Response-Suppress', email._headers)

        msg = email.message()
        self.assertNotIn('X-Auto-Response-Suppress', msg)

    def test_message_with_extra_headers_dict(self):
        """Testing EmailMessage.message with extra headers as a dict"""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             headers={
                                 'X-Foo': 'Bar',
                             })

        message = email.message()

        self.assertIn('X-Foo', message)
        self.assertEqual(message['X-Foo'], 'Bar')

    def test_message_with_extra_headers_multivalue_dict(self):
        """Testing EmailMessage.message with extra headers as a MultiValueDict
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

        message = email.message()

        self.assertIn('X-Foo', message)
        self.assertEqual(set(message.get_all('X-Foo')),
                         set(header_values))

    def test_send_with_unicode_subject(self):
        """Testing EmailMessage.send with a Unicode subject"""
        email = EmailMessage(subject='\U0001f604',
                             text_body='This is a test',
                             html_body='<p>This is a test</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        message = email.message()
        self.assertEqual(message['Subject'], '=?utf-8?b?8J+YhA==?=')

    def test_send_with_unicode_body(self):
        """Testing EmailMessage.send with a Unicode body"""
        email = EmailMessage(subject='Test email',
                             text_body='\U0001f604',
                             html_body='<p>\U0001f604</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        message = email.message()
        self.assertEqual(message.get_payload(0).get_payload(decode=True),
                         b'\xf0\x9f\x98\x84')
        self.assertEqual(message.get_payload(1).get_payload(decode=True),
                         b'<p>\xf0\x9f\x98\x84</p>')


class UtilsTests(TestCase):
    """Unit tests for djblets.mail.utils."""

    def test_build_email_address_with_full_name(self):
        """Testing build_email_address with full name"""
        self.assertEqual(build_email_address(email='test@example.com',
                                             full_name='Test User'),
                         'Test User <test@example.com>')

    def test_build_email_address_with_unicode(self):
        """Testing build_email_address with Unicode characters"""
        self.assertEqual(build_email_address(email='test@example.com',
                                             full_name='Tést Üser'),
                         'Tést Üser <test@example.com>')

    def test_build_email_address_without_full_name(self):
        """Testing build_email_address without full name"""
        self.assertEqual(build_email_address(email='test@example.com'),
                         'test@example.com')

    def test_build_email_address_for_user(self):
        """Testing build_email_address_for_user"""
        user = User.objects.create(username='test',
                                   first_name='Test',
                                   last_name='User',
                                   email='test@example.com')

        self.assertEqual(build_email_address_for_user(user),
                         'Test User <test@example.com>')

    def test_build_email_address_for_user_with_unicode(self):
        """Testing build_email_address_for_user with Unicode characters"""
        user = User.objects.create(username='test',
                                   first_name='Tést',
                                   last_name='Üser',
                                   email='test@example.com')

        self.assertEqual(build_email_address_for_user(user),
                         'Tést Üser <test@example.com>')

    def test_build_email_address_via_service(self):
        """Testing test_build_email_address_via_service"""
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                full_name='Test User',
                service_name='My Service',
                sender_email='noreply@example.com'),
            'Test User via My Service <noreply@example.com>')

    def test_build_email_address_via_service_with_unicode_user_name(self):
        """Testing test_build_email_address_via_service with Unicode
        characters in user's name
        """
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                full_name='Tést Üser',
                service_name='My Service',
                sender_email='noreply@example.com'),
            'Tést Üser via My Service <noreply@example.com>')

    def test_build_email_address_via_service_with_unicode_service(self):
        """Testing test_build_email_address_via_service with Unicode
        characters in service name
        """
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                full_name='Test User',
                service_name='My Sérvice',
                sender_email='noreply@example.com'),
            'Test User via My Sérvice <noreply@example.com>')

    def test_build_email_address_via_service_without_full_name(self):
        """Testing test_build_email_address_via_service without full name"""
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                service_name='My Service',
                sender_email='noreply@example.com'),
            'test via My Service <noreply@example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME='My Service')
    def test_build_email_address_via_service_with_service_name_setting(self):
        """Testing test_build_email_address_via_service with service name
        from settings.EMAIL_DEFAULT_SENDER_SERVICE_NAME
        """
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                full_name='Test User',
                sender_email='noreply@example.com'),
            'Test User via My Service <noreply@example.com>')

    @override_settings(EMAIL_DEFAULT_SENDER_SERVICE_NAME=None)
    def test_build_email_address_via_service_with_computed_service_name(self):
        """Testing test_build_email_address_via_service with service name
        computed from sender e-mail
        """
        self.assertEqual(
            build_email_address_via_service(
                email='test@example.com',
                full_name='Test User',
                sender_email='noreply@example.com'),
            '"Test User via example.com" <noreply@example.com>')

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    def test_build_email_address_via_service_with_sender_email_setting(self):
        """Testing test_build_email_address_via_service with sender e-mail
        from settings.DEFAULT_FROM_EMAIL
        """
        self.assertEqual(
            build_email_address_via_service(
                full_name='Test User',
                email='test@example.com',
                service_name='My Service'),
            'Test User via My Service <noreply@example.com>')
