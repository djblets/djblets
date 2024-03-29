"""Tests for djblets.gravatars."""

from hashlib import md5

from django.contrib.auth.models import User
from django.template import Context, Template

from djblets.gravatars import get_gravatar_url, get_gravatar_url_for_email
from djblets.testing.testcases import TagTest, TestCase


class GravatarTests(TestCase):
    """Tests for gravatar functions."""

    _URL_BASE = 'https://secure.gravatar.com/avatar/'

    def test_get_gravatar_url_for_email_uppercase(self):
        """Testing get_gravatar_url_for_email with uppercase characters"""
        self.assertEqual(get_gravatar_url_for_email(email='FOO@EXAMPLE.COM'),
                         get_gravatar_url_for_email(email='foo@example.com'))
        self.assertEqual(
            get_gravatar_url_for_email(email='foo@example.com'),
            '%s%s' % (self._URL_BASE, md5(b'foo@example.com').hexdigest()))

    def test_get_gravatar_url_for_email_whitespace(self):
        """Testing get_gravatar_url_for_email with whitespace characters"""
        self.assertEqual(get_gravatar_url_for_email(email=' foo@example.com '),
                         get_gravatar_url_for_email(email='foo@example.com'))

    def test_get_gravatar_url_for_email_unicode(self):
        """Testing get_gravatar_url_for_email with unicode characters"""
        raw_email = 'こんにちは@example.com'
        encoded_email = raw_email.encode('utf-8')

        self.assertEqual(get_gravatar_url_for_email(email=raw_email),
                         get_gravatar_url_for_email(email=encoded_email))
        self.assertEqual(
            get_gravatar_url_for_email(email=raw_email),
            '%s%s' % (self._URL_BASE, md5(encoded_email).hexdigest()))

    def test_get_gravatar_url_for_email_query_order(self):
        """Testing get_gravatar_url_for_email query string ordering"""
        email = 'foo@example.com'

        with self.settings(GRAVATAR_RATING='G',
                           GRAVATAR_DEFAULT='my-default'):
            self.assertEqual(
                get_gravatar_url_for_email(email='foo@example.com', size=128),
                '%s%s?s=128&r=G&d=my-default'
                % (self._URL_BASE, md5(email.encode('utf-8')).hexdigest()))

    def test_get_gravatar_url_uppercase(self):
        """Testing get_gravatar_url with uppercase characters"""
        user = User.objects.create_user(username='user',
                                        email='FOO@EXAMPLE.COM')
        self.assertEqual(get_gravatar_url(user=user),
                         get_gravatar_url_for_email(email='foo@example.com'))

    def test_get_gravatar_url_whitespace(self):
        """Testing get_gravatar_url with whitespace characters"""
        user = User.objects.create_user(username='user',
                                        email=' foo@example.com ')
        self.assertEqual(get_gravatar_url(user=user),
                         get_gravatar_url_for_email(email='foo@example.com'))

    def test_get_gravatar_url_for_unicode(self):
        """Testing get_gravatar_url with unicode characters"""
        raw_email = 'こんにちは@example.com'
        encoded_email = raw_email.encode('utf-8')
        user = User.objects.create_user(username='user', email=raw_email)
        self.assertEqual(get_gravatar_url(user=user),
                         get_gravatar_url_for_email(email=encoded_email))


class TagTests(TagTest):
    """Unit tests for gravatars template tags."""

    def test_gravatar_xss(self):
        """Testing {% gravatar %} doesn't allow XSS injection"""
        user = User(username='test',
                    first_name='"><script>alert(1);</script><"',
                    email='test@example.com')

        t = Template('{% load gravatars %}'
                     '{% gravatar user 32 %}')

        self.assertEqual(
            t.render(Context({
                'user': user,
            })),
            '<img src="https://secure.gravatar.com/avatar/'
            '55502f40dc8b7c769880b10874abc9d0?s=32" width="32" height="32" '
            'alt="&quot;&gt;&lt;script&gt;alert(1);&lt;/script&gt;&lt;&quot;" '
            'class="gravatar"/>')

    def test_gravatar_url_tag(self):
        """Testing gravatar_url template tag"""
        t = Template('{% load gravatars %}'
                     '{% gravatar_url "test@example.com" 32 %}')

        self.assertEqual(
            t.render(Context({})),
            'https://secure.gravatar.com/avatar/'
            '55502f40dc8b7c769880b10874abc9d0?s=32')
