from __future__ import unicode_literals

from django.core import mail
from django.core.cache import cache
from django.utils.datastructures import MultiValueDict
from dns import resolver as dns_resolver
from dns.rdtypes.ANY.TXT import TXT
from kgb import SpyAgency

from djblets.mail.dmarc import DmarcPolicy, get_dmarc_record
from djblets.mail.message import EmailMessage
from djblets.testing.testcases import TestCase


_CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class DmarcTests(SpyAgency, TestCase):
    """Tests for DMARC support."""

    def setUp(self):
        super(DmarcTests, self).setUp()

        self.dmarc_txt_records = {}

        self.spy_on(dns_resolver.query, call_fake=self._dns_query)
        cache.clear()

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

        self.assertEqual(len(dns_resolver.query.spy.calls), 1)

    def _dns_query(self, qname, rdtype, *args, **kwargs):
        try:
            return [TXT(1, 16, [self.dmarc_txt_records[qname]])]
        except KeyError:
            raise dns_resolver.NXDOMAIN


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
