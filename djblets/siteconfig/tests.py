#
# tests.py -- Unit tests for classes in djblets.siteconfig
#
# Copyright (c) 2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache

from djblets.siteconfig.django_settings import apply_django_settings, \
                                               mail_settings_map
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.testing import TestCase


class SiteConfigTest(TestCase):
    def setUp(self):
        self.siteconfig = SiteConfiguration(site=Site.objects.get_current())
        self.siteconfig.save()

    def tearDown(self):
        self.siteconfig.delete()
        SiteConfiguration.objects.clear_cache()

    def testMailAuthDeserialize(self):
        """Testing mail authentication settings deserialization"""
        # This is bug 1476. We deserialized the e-mail settings to Unicode
        # strings automatically, but this broke mail sending on some setups.
        # The HMAC library is incompatible with Unicode strings in more recent
        # Python 2.6 versions. Now we deserialize as a string. This test
        # ensures that these settings never break again.

        username = u'myuser'
        password = u'mypass'

        self.siteconfig.set('mail_host_user', username)
        self.siteconfig.set('mail_host_password', password)
        apply_django_settings(self.siteconfig, mail_settings_map)

        self.assertEqual(settings.EMAIL_HOST_USER, username)
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, password)
        self.assertEqual(type(settings.EMAIL_HOST_USER), str)
        self.assertEqual(type(settings.EMAIL_HOST_PASSWORD), str)

        # Simulate the failure point in HMAC
        trans_5C = "".join ([chr (x ^ 0x5C) for x in xrange(256)])
        settings.EMAIL_HOST_USER.translate(trans_5C)
        settings.EMAIL_HOST_PASSWORD.translate(trans_5C)

    def testSynchronization(self):
        """Testing synchronizing SiteConfigurations through cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def testSynchronizationExpiredCache(self):
        """Testing synchronizing SiteConfigurations with an expired cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        cache.delete('%s:siteconfig:%s:generation' %
                     (siteconfig2.site.domain, siteconfig2.id))

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)
