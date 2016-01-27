from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template

from djblets.testing.testcases import TagTest


class DummyRequest(object):
    def __init__(self, is_secure=False):
        self._is_secure = is_secure

    def is_secure(self):
        return self._is_secure


class TagTests(TagTest):
    """Unit tests for gravatars template tags."""
    def test_gravatar_xss(self):
        """Testing {% gravatar %} doesn't allow XSS injection"""
        user = User(username='test',
                    first_name='"><script>alert(1);</script><"',
                    email='test@example.com')

        context = {
            'request': DummyRequest(),
            'user': user,
        }

        t = Template('{% load gravatars %}'
                     '{% gravatar user 32 %}')

        self.assertEqual(
            t.render(Context(context)),
            '<img src="http://www.gravatar.com/avatar/'
            '55502f40dc8b7c769880b10874abc9d0?s=32" width="32" height="32" '
            'alt="&quot;&gt;&lt;script&gt;alert(1);&lt;/script&gt;&lt;&quot;" '
            'class="gravatar"/>')

    def test_gravatar_url_tag(self):
        """Testing gravatar_url template tag"""
        t = Template('{% load gravatars %}'
                     '{% gravatar_url "test@example.com" 32 %}')

        self.assertEqual(
            t.render(Context({
                'request': DummyRequest(),
            })),
            'http://www.gravatar.com/avatar/55502f40dc8b7c769880b10874abc9d0?'
            's=32')

    def test_gravatar_url_tag_https(self):
        """Testing gravatar_url template tag for HTTPS requests"""
        t = Template('{% load gravatars %}'
                     '{% gravatar_url "test@example.com" 32 %}')

        self.assertEqual(
            t.render(Context({
                'request': DummyRequest(is_secure=True),
            })),
            'https://secure.gravatar.com/avatar/'
            '55502f40dc8b7c769880b10874abc9d0?s=32')
