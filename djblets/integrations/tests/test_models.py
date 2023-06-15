from djblets.integrations.integration import Integration
from djblets.integrations.manager import IntegrationManager
from djblets.integrations.tests.models import IntegrationConfig
from djblets.integrations.tests.testcases import IntegrationsTestCase


class DummyIntegration1(Integration):
    name = 'Dummy'

    default_settings = {
        'foo': 'default-foo',
    }

    def initialize(self) -> None:
        pass


class IntegrationConfigTests(IntegrationsTestCase):
    """Unit tests for djblets.integrations.models.BaseIntegrationConfig."""

    ######################
    # Instance variables #
    ######################

    integration: Integration
    manager: IntegrationManager

    def setUp(self) -> None:
        super().setUp()

        manager = IntegrationManager(IntegrationConfig)
        IntegrationConfig.manager = manager
        self.manager = manager

        self.integration = manager.register_integration_class(
            DummyIntegration1)
        self.config = self.integration.create_config(name='Test Config')

    def tearDown(self) -> None:
        IntegrationConfig.manager = None

        super().tearDown()

    def test_integration(self) -> None:
        """Testing BaseIntegrationConfig.integration"""
        self.assertIs(self.config.integration, self.integration)

    def test_get(self) -> None:
        """Testing BaseIntegrationConfig.get"""
        self.config.settings['foo'] = 'bar'
        self.assertEqual(self.config.get('foo'), 'bar')

    def test_get_with_integration_defaults(self) -> None:
        """Testing BaseIntegrationConfig.get with integration defaults"""
        self.assertEqual(self.config.get('foo'), 'default-foo')

    def test_get_with_default(self) -> None:
        """Testing BaseIntegrationConfig.get with default"""
        self.assertEqual(self.config.get('new-key', 'my-default'),
                         'my-default')

    def test_set(self) -> None:
        """Testing BaseIntegrationConfig.set"""
        self.config.set('my-key', 'my-value')
        self.assertEqual(self.config.settings.get('my-key'), 'my-value')

    def test_str_with_available_integration(self) -> None:
        """Testing BaseIntegrationConfig.__str__ with available integration"""
        self.assertEqual(str(self.config), 'Test Config (Dummy)')

    def test_str_without_available_integration(self) -> None:
        """Testing BaseIntegrationConfig.__str__ without available integration
        """
        self.config.integration_id = 'foo.bar.BadIntegration'

        self.assertEqual(str(self.config),
                         'Test Config (foo.bar.BadIntegration)')
