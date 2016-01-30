from __future__ import unicode_literals

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.mixins import DynamicConfigPageMixin
from djblets.configforms.pages import ConfigPage
from djblets.configforms.registry import ConfigPageRegistry
from djblets.registries.errors import RegistrationError
from djblets.testing.testcases import TestCase


class DynamicConfigPage(DynamicConfigPageMixin, ConfigPage):
    pass


class TestFormA(ConfigPageForm):
    form_id = 'form-a'


class TestFormB(ConfigPageForm):
    form_id = 'form-b'


class TestPageOne(DynamicConfigPage):
    page_id = 'page-b'
    form_classes = [TestFormB]


class TestPageTwo(DynamicConfigPage):
    page_id = 'page-ab'
    form_classes = [TestFormA, TestFormB]


class ConfigPageRegistryTests(TestCase):
    """Tests for djblets.configforms.registry.ConfigPageRegistry."""

    @classmethod
    def setUpClass(cls):
        super(ConfigPageRegistryTests, cls).setUpClass()
        cls.registry = ConfigPageRegistry()
        DynamicConfigPage.registry = cls.registry

    def tearDown(self):
        self.registry.reset()

    def test_reset(self):
        """Testing ConfigPageRegistry.reset"""
        self.assertSetEqual(set(self.registry), set())
        self.assertSetEqual(set(self.registry._forms), set())
        self.registry.register(TestPageOne)
        self.registry.reset()

        self.assertSetEqual(set(self.registry), set())
        self.assertSetEqual(set(self.registry._forms), set())

    def test_partial_register_page(self):
        """Testing ConfigPageRegistry.register when the registration is
        partially successful
        """
        self.registry.register(TestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.register(TestPageTwo)

        self.assertEqual(set(self.registry), {TestPageOne})

    def test_register_page_with_duplicate(self):
        """Testing ConfigPageRegistry.register when registering a page that
        contains pre-registered forms
        """
        class TestPage(DynamicConfigPage):
            page_id = 'test-page'
            form_classes = [TestFormB]

        self.registry.register(TestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.register(TestPage)

    def test_add_form_to_page(self):
        """Testing ConfigPageRegistry.add_form_to_page"""
        self.registry.register(TestPageOne)
        self.registry.add_form_to_page(TestPageOne, TestFormA)

        self.assertSetEqual(set(TestPageOne.form_classes),
                            {TestFormA, TestFormB})
        self.assertSetEqual(set(self.registry._forms),
                            {TestFormA, TestFormB})

    def test_remove_form_from_page(self):
        """Testing ConfigPageRegistry.remove_form_from_page"""
        self.registry.register(TestPageOne)
        self.registry.remove_form_from_page(TestPageOne, TestFormB)

        self.assertListEqual(list(TestPageOne.form_classes), [])
        self.assertListEqual(list(self.registry._forms), [])

    def test_add_duplicate_form_to_page(self):
        """Testing ConfigPageRegistry.add_form_to_page with a duplicate form"""
        self.registry.register(TestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.add_form_to_page(TestPageOne, TestFormB)

        self.assertEqual(TestPageOne.form_classes, [TestFormB])

    def test_default_form_classes(self):
        """Testing DynamicConfigPageMixin._default_form_classes persistence"""
        self.registry.register(TestPageOne)
        self.assertListEqual(TestPageOne.form_classes, [TestFormB])
        self.registry.add_form_to_page(TestPageOne, TestFormA)
        self.assertSetEqual(set(TestPageOne.form_classes),
                            {TestFormA, TestFormB})

        self.registry.unregister(TestPageOne)
        self.assertListEqual(TestPageOne.form_classes, [])

        self.registry.register(TestPageOne)
        self.assertListEqual(TestPageOne.form_classes, [TestFormB])

    def test_empty_default_form_classes_for_page(self):
        """Testing DynamicConfigPageMixin._default_form_classes with no form
        classes
        """
        class TestPage(DynamicConfigPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        self.registry.register(TestPage)
        self.assertListEqual(TestPage.form_classes, [])

        self.registry.add_form_to_page(TestPage, TestFormA)
        self.assertListEqual(TestPage.form_classes, [TestFormA])

        self.registry.unregister(TestPage)
        self.assertListEqual(TestPage.form_classes, [])

        self.registry.register(TestPage)
        self.assertListEqual(TestPage.form_classes, [])
