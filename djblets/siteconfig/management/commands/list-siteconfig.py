from django.core.management.base import NoArgsCommand
from django.utils import simplejson

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Lists the site configuration."""
    def handle_noargs(self, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        print simplejson.dumps(siteconfig.settings, indent=2)
