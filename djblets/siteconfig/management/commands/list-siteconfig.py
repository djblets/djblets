from __future__ import unicode_literals

import json

from django.core.management.base import BaseCommand

from djblets.siteconfig.models import SiteConfiguration


class Command(BaseCommand):
    """Lists the site configuration."""

    def handle(self, *args, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        self.stdout.write(json.dumps(siteconfig.settings, indent=2))
