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


class EmailMessageTests(SpyAgency, TestCase):
    """Tests for djblets.mail.message.EmailMessage."""

    def setUp(self):
        super(EmailMessageTests, self).setUp()

        mail.outbox = []

    def test_init_with_html_body(self):
        """Testing EmailMessage.__init__ with html_body="""
        # auto_generated is True by default, so test with that case to ensure
        # it doesn't unintentionally change.
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertEqual(email.alternatives,
                         [('<p>This is a test.</p>', 'text/html')])

    def test_message_with_from(self):
        """Testing EmailMessage.message with from_email="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'])

        self.assertNotIn('Sender', email._headers)
        self.assertNotIn('X-Sender', email._headers)
        self.assertNotIn('From', email.extra_headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertIn('Reply-To', email._headers)
        self.assertEqual(email.from_email, 'doc@example.com')
        self.assertEqual(email._headers['Reply-To'], 'doc@example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Reply-To'], 'doc@example.com')

    def test_message_with_sender(self):
        """Testing EmailMessage.message with sender="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             html_body='<p>This is a test.</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        self.assertIn('Sender', email._headers)
        self.assertIn('X-Sender', email._headers)
        self.assertNotIn('From', email.extra_headers)
        self.assertNotIn('From', email._headers)
        self.assertNotIn('Sender', email.extra_headers)
        self.assertNotIn('X-Sender', email.extra_headers)
        self.assertEqual(email._headers['Sender'], 'noreply@example.com')
        self.assertEqual(email._headers['X-Sender'], 'noreply@example.com')

        msg = email.message()
        self.assertEqual(msg['From'], 'doc@example.com')
        self.assertEqual(msg['Sender'], 'noreply@example.com')
        self.assertEqual(msg['X-Sender'], 'noreply@example.com')

    def test_message_with_in_reply_to(self):
        """Testing EmailMessage.message with in_reply_to="""
        email = EmailMessage(subject='Test email',
                             text_body='This is a test.',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             in_reply_to='someone@example.com')

        self.assertIn('In-Reply-To', email._headers)
        self.assertIn('References', email._headers)
        self.assertEqual(email._headers['In-Reply-To'], 'someone@example.com')
        self.assertEqual(email._headers['References'], 'someone@example.com')

        msg = email.message()
        self.assertEqual(msg['In-Reply-To'], 'someone@example.com')
        self.assertEqual(msg['References'], 'someone@example.com')

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
        email = EmailMessage(subject='\ud83d\ude04',
                             text_body='This is a test',
                             html_body='<p>This is a test</p>',
                             from_email='doc@example.com',
                             to=['sleepy@example.com'],
                             sender='noreply@example.com')

        with self.settings(EMAIL_BACKEND=_CONSOLE_EMAIL_BACKEND):
            email.send()

    def test_send_with_unicode_body(self):
        """Testing EmailMessage.send with a Unicode body"""
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
