from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template

from djblets.testing.testcases import TagTest


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
