"""Unit tests for djblets.db.query."""

from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.db.models import (ForeignKey,
                              ManyToManyField,
                              ManyToManyRel,
                              ManyToOneRel,
                              OneToOneField,
                              OneToOneRel,
                              Q)

from djblets.privacy.models import StoredConsentData
from djblets.db.query import get_object_cached_field, prefix_q
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class GetObjectCachedFieldTests(TestCase):
    """Unit tests for get_object_cached_field().

    Version Added:
        5.3
    """

    def test_with_select_related(self) -> None:
        """Testing get_object_cached_field with select_related() value found"""
        user1 = User.objects.create(username='test-user')
        consent_data = StoredConsentData.objects.create(user=user1)

        user2 = (
            User.objects
            .filter(username='test-user')
            .select_related('storedconsentdata')
        ).first()

        assert user2 is not None

        with self.assertNumQueries(0):
            self.assertEqual(
                get_object_cached_field(user2, 'storedconsentdata'),
                consent_data)

    def test_with_select_related_and_none(self) -> None:
        """Testing get_object_cached_field with select_related() value as None
        """
        User.objects.create(username='test-user')

        user = (
            User.objects
            .filter(username='test-user')
            .select_related('storedconsentdata')
        ).first()

        assert user is not None

        with self.assertNumQueries(0):
            self.assertIsNone(get_object_cached_field(user,
                                                      'storedconsentdata'))

    def test_with_prefetch_related_fkey(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        direct ForeignKey relation with value found
        """
        self.assertIsInstance(
            SiteConfiguration._meta.get_field('site').remote_field,
            ManyToOneRel)

        site = Site.objects.get_current()
        SiteConfiguration.objects.create(site=site)

        siteconfigs = list(
            SiteConfiguration.objects
            .prefetch_related('site')
        )

        self.assertEqual(len(siteconfigs), 1)
        siteconfig = siteconfigs[0]

        with self.assertNumQueries(0):
            self.assertEqual(
                get_object_cached_field(siteconfig, 'site'),
                site)

    def test_with_prefetch_related_fkey_reverse(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        reverse ForeignKey relation with value found
        """
        self.assertIsInstance(Site._meta.get_field('config').remote_field,
                              ForeignKey)

        siteconfig = SiteConfiguration.objects.create(
            site=Site.objects.get_current())

        sites = list(
            Site.objects
            .prefetch_related('config')
        )

        self.assertEqual(len(sites), 1)
        site = sites[0]

        with self.assertNumQueries(0):
            self.assertEqual(
                get_object_cached_field(site, 'config'),
                [siteconfig])

    def test_with_prefetch_related_m2m(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        direct ManyToManyField relation with value found
        """
        self.assertIsInstance(User._meta.get_field('groups').remote_field,
                              ManyToManyRel)

        group = Group.objects.create(name='group1')

        user1 = User.objects.create(username='test-user')
        user1.groups.add(group)

        users = list(
            User.objects
            .filter(username='test-user')
            .prefetch_related('groups')
        )

        self.assertEqual(len(users), 1)
        user2 = users[0]

        with self.assertNumQueries(0):
            self.assertEqual(get_object_cached_field(user2, 'groups'),
                             [group])

    def test_with_prefetch_related_m2m_reverse(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        reverse ManyToManyField relation with value found
        """
        self.assertIsInstance(Group._meta.get_field('user').remote_field,
                              ManyToManyField)

        group = Group.objects.create(name='group1')

        user1 = User.objects.create(username='test-user')
        user1.groups.add(group)

        groups = list(
            Group.objects
            .prefetch_related('user_set')
        )

        self.assertEqual(len(groups), 1)
        group2 = groups[0]

        with self.assertNumQueries(0):
            self.assertEqual(get_object_cached_field(group2, 'user'),
                             [user1])

    def test_with_prefetch_related_oto(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        direct OneToOneField relation with value found
        """
        self.assertIsInstance(
            StoredConsentData._meta.get_field('user').remote_field,
            OneToOneRel)

        user1 = User.objects.create(username='test-user')
        StoredConsentData.objects.create(user=user1)

        consent_datas = list(
            StoredConsentData.objects
            .prefetch_related('user')
        )

        self.assertEqual(len(consent_datas), 1)
        consent_data2 = consent_datas[0]

        with self.assertNumQueries(0):
            self.assertEqual(
                get_object_cached_field(consent_data2, 'user'),
                user1)

    def test_with_prefetch_related_oto_reverse(self) -> None:
        """Testing get_object_cached_field with prefetch_related() on
        reverse OneToOneField relation with value found
        """
        self.assertIsInstance(
            User._meta.get_field('storedconsentdata').remote_field,
            OneToOneField)

        user1 = User.objects.create(username='test-user')
        consent_data = StoredConsentData.objects.create(user=user1)

        users = list(
            User.objects
            .filter(username='test-user')
            .prefetch_related('storedconsentdata')
        )

        self.assertEqual(len(users), 1)
        user2 = users[0]

        with self.assertNumQueries(0):
            self.assertEqual(
                get_object_cached_field(user2, 'storedconsentdata'),
                consent_data)


class PrefixTests(TestCase):
    """Tests for djblets.db.query.prefix_q."""

    def test_simple(self):
        """Testing prefix_q prefixes simple expressions"""
        self.assertEqual(
            str(prefix_q('fk', Q(hello='goodbye'))),
            str(Q(fk__hello='goodbye')))

    def test_nested(self):
        """Testing prefix_q prefixes nested expressions"""
        self.assertEqual(
            str(prefix_q('fk',
                         Q(foo='foo') |
                         (Q(bar='bar') &
                          Q(baz='baz')))),
            str(Q(fk__foo='foo') |
                (Q(fk__bar='bar') &
                 Q(fk__baz='baz'))))

    def test_bytestring_result(self):
        """Testing that prefix_q generates byte strings for key names"""
        q = prefix_q('fk', Q(foo='bar'))
        self.assertEqual(len(q.children), 1)
        self.assertIs(type(q.children[0]), tuple)
        self.assertIsInstance(q.children[0][0], str)
