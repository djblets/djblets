"""Unit tests for djblets.configforms.registry.ConfigPageRegistry."""

from kgb import SpyAgency

from djblets.configforms.forms import ConfigPageForm
from djblets.configforms.mixins import DynamicConfigPageMixin
from djblets.configforms.pages import ConfigPage
from djblets.configforms.registry import ConfigPageRegistry
from djblets.registries.errors import RegistrationError
from djblets.testing.testcases import TestCase


class DynamicConfigPage(DynamicConfigPageMixin, ConfigPage):
    pass


class MyTestFormA(ConfigPageForm):
    form_id = 'form-a'


class MyTestFormB(ConfigPageForm):
    form_id = 'form-b'


class MyTestPageOne(DynamicConfigPage):
    page_id = 'page-b'
    form_classes = [MyTestFormB]


class MyTestPageTwo(DynamicConfigPage):
    page_id = 'page-ab'
    form_classes = [MyTestFormA, MyTestFormB]


class ConfigPageRegistryTests(SpyAgency, TestCase):
    """Unit tests for djblets.configforms.registry.ConfigPageRegistry."""

    @classmethod
    def setUpClass(cls):
        super(ConfigPageRegistryTests, cls).setUpClass()
        cls.registry = ConfigPageRegistry()
        DynamicConfigPage.registry = cls.registry

    def tearDown(self):
        super(ConfigPageRegistryTests, self).tearDown()

        self.registry.reset()
        MyTestPageOne.form_classes = [MyTestFormB]
        MyTestPageTwo.formClasses = [MyTestFormA, MyTestFormB]

    def test_reset(self):
        """Testing ConfigPageRegistry.reset"""
        self.assertSetEqual(set(self.registry), set())
        self.assertSetEqual(set(self.registry._forms), set())
        self.registry.register(MyTestPageOne)
        self.registry.reset()

        self.assertSetEqual(set(self.registry), set())
        self.assertSetEqual(set(self.registry._forms), set())

    def test_partial_register_page(self):
        """Testing ConfigPageRegistry.register when the registration is
        partially successful
        """
        self.registry.register(MyTestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.register(MyTestPageTwo)

        self.assertEqual(set(self.registry), {MyTestPageOne})

    def test_register_page_with_duplicate(self):
        """Testing ConfigPageRegistry.register when registering a page that
        contains pre-registered forms
        """
        class MyTestPage(DynamicConfigPage):
            page_id = 'test-page'
            form_classes = [MyTestFormB]

        self.registry.register(MyTestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.register(MyTestPage)

    def test_add_form_to_page(self):
        """Testing ConfigPageRegistry.add_form_to_page"""
        self.registry.register(MyTestPageOne)
        self.registry.add_form_to_page(MyTestPageOne, MyTestFormA)

        self.assertSetEqual(set(MyTestPageOne.form_classes),
                            {MyTestFormA, MyTestFormB})
        self.assertSetEqual(set(self.registry._forms),
                            {MyTestFormA, MyTestFormB})

    def test_remove_form_from_page(self):
        """Testing ConfigPageRegistry.remove_form_from_page"""
        self.registry.register(MyTestPageOne)
        self.registry.remove_form_from_page(MyTestPageOne, MyTestFormB)

        self.assertListEqual(list(MyTestPageOne.form_classes), [])
        self.assertListEqual(list(self.registry._forms), [])

    def test_add_duplicate_form_to_page(self):
        """Testing ConfigPageRegistry.add_form_to_page with a duplicate form"""
        self.registry.register(MyTestPageOne)

        with self.assertRaises(RegistrationError):
            self.registry.add_form_to_page(MyTestPageOne, MyTestFormB)

        self.assertEqual(MyTestPageOne.form_classes, [MyTestFormB])

    def test_default_form_classes(self):
        """Testing DynamicConfigPageMixin._default_form_classes persistence"""
        self.registry.register(MyTestPageOne)
        self.assertListEqual(MyTestPageOne.form_classes, [MyTestFormB])
        self.registry.add_form_to_page(MyTestPageOne, MyTestFormA)
        self.assertSetEqual(set(MyTestPageOne.form_classes),
                            {MyTestFormA, MyTestFormB})

        self.registry.unregister(MyTestPageOne)
        self.assertListEqual(MyTestPageOne.form_classes, [])

        self.registry.register(MyTestPageOne)
        self.assertListEqual(MyTestPageOne.form_classes, [MyTestFormB])

    def test_empty_default_form_classes_for_page(self):
        """Testing DynamicConfigPageMixin._default_form_classes with no form
        classes
        """
        class MyTestPage(DynamicConfigPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        self.registry.register(MyTestPage)
        self.assertListEqual(MyTestPage.form_classes, [])

        self.registry.add_form_to_page(MyTestPage, MyTestFormA)
        self.assertListEqual(MyTestPage.form_classes, [MyTestFormA])

        self.registry.unregister(MyTestPage)
        self.assertListEqual(MyTestPage.form_classes, [])

        self.registry.register(MyTestPage)
        self.assertListEqual(MyTestPage.form_classes, [])

    def test_add_form_to_page_populate(self):
        """Testing ConfigPageRegistry.add_form_to_page populates itself and the
         ConfigPageFormRegistry
         """
        class TestRegistry(ConfigPageRegistry):
            def get_defaults(self):
                yield MyTestPageOne

        registry = TestRegistry()

        self.spy_on(registry.populate)
        self.spy_on(registry._forms.populate)

        registry.add_form_to_page(MyTestPageOne, MyTestFormA)

        self.assertTrue(registry.populate.spy.called)
        self.assertTrue(registry._forms.populate.spy.called)
        self.assertEqual(set(registry._forms), {MyTestFormA, MyTestFormB})

    def test_add_form_to_page_populate_duplicate(self):
        """Testing ConfigPageRegistry.add_form_to_page with an already
        registered page raises an error due to population
        """
        class TestRegistry(ConfigPageRegistry):
            def get_defaults(self):
                yield MyTestPageOne

        registry = TestRegistry()

        with self.assertRaises(registry.already_registered_error_class):
            registry.add_form_to_page(MyTestPageOne, MyTestFormB)

        self.assertEqual(set(registry._forms), {MyTestFormB})

    def test_remove_form_from_page_populate(self):
        """Testing ConfigPageRegistry.remove_form_from_page populates itself
        and the ConfigPgaeFormRegistry
        """
        class TestRegistry(ConfigPageRegistry):
            def get_defaults(self):
                yield MyTestPageOne

        registry = TestRegistry()

        self.spy_on(registry.populate)
        self.spy_on(registry._forms.populate)

        registry.remove_form_from_page(MyTestPageOne, MyTestFormB)

        self.assertTrue(registry.populate.spy.called)
        self.assertTrue(registry._forms.populate.spy.called)
        self.assertEqual(set(registry._forms), set())

    def test_remove_form_from_page_populate_unregistered(self):
        """Testing ConfigPageForm.remove_form_from_page with an unregistered
        page raises an error due to population
        """
        class TestRegistry(ConfigPageRegistry):
            def get_defaults(self):
                yield MyTestPageOne

        registry = TestRegistry()

        with self.assertRaises(registry.lookup_error_class):
            registry.remove_form_from_page(MyTestPageOne, MyTestFormA)

        self.assertEqual(set(registry._forms), {MyTestFormB})
