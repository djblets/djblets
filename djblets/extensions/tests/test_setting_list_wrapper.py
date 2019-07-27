"""Unit tests for djblets.extensions.manager.SettingListWrapper."""

from __future__ import unicode_literals

from django.conf import settings

from djblets.extensions.manager import SettingListWrapper
from djblets.testing.testcases import TestCase


class SettingListWrapperTests(TestCase):
    """Unit tests for djblets.extensions.manager.SettingListWrapper."""

    def test_loading_from_setting(self):
        """Testing SettingListWrapper constructor loading from settings"""
        settings.TEST_SETTING_LIST = ['item1', 'item2']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        self.assertEqual(wrapper.ref_counts.get('item2'), 1)

    def test_add_with_new_item(self):
        """Testing SettingListWrapper.add with new item"""
        settings.TEST_SETTING_LIST = []
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)

    def test_add_with_existing_item(self):
        """Testing SettingListWrapper.add with existing item"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 2)

    def test_remove_with_ref_count_1(self):
        """Testing SettingListWrapper.remove with ref_count == 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, [])
        self.assertFalse('item1' in wrapper.ref_counts)

    def test_remove_with_ref_count_gt_1(self):
        """Testing SettingListWrapper.remove with ref_count > 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(wrapper.ref_counts.get('item1'), 2)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
