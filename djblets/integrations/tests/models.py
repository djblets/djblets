from __future__ import unicode_literals

from djblets.integrations.models import BaseIntegrationConfig


class IntegrationConfig(BaseIntegrationConfig):
    def get_integration_manager(self):
        return self.manager
