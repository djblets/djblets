from optparse import make_option

from django.core.management.base import CommandError, NoArgsCommand

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Displays a setting in the site configuration."""
    option_list = NoArgsCommand.option_list + (
        make_option('--key', action='store', dest='key',
                    help='The existing key to display (dot-separated)'),
    )

    def handle_noargs(self, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        key = options['key']

        if key is None:
            raise CommandError('--key must be provided')

        path = key.split('.')
        node = siteconfig.settings
        valid_key = True

        for item in path[:-1]:
            try:
                node = node[item]
            except KeyError:
                valid_key = False

        if valid_key:
            key_basename = path[-1]

            if key_basename not in node:
                valid_key = False

        if not valid_key:
            raise CommandError("'%s' is not a valid settings key" % key)

        print node[key_basename]
