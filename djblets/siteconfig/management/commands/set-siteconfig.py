"""Management command for setting site configuration."""

from typing import Type

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from djblets.siteconfig.models import SiteConfiguration


class Command(BaseCommand):
    """Sets a setting in the site configuration.

    This cannot create new settings. It can only set existing ones.
    """

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (object):
                The argument parser to add to.
        """
        parser.add_argument(
            '--key',
            action='store',
            dest='key',
            help=_('The existing key to modify (dot-separated)'))

        parser.add_argument(
            '--value',
            action='store',
            dest='value',
            help=_('The value to store'))

    def handle(self, *args, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        key = options['key']
        value = options['value']

        if key is None:
            raise CommandError(_('--key must be provided'))

        if value is None:
            raise CommandError(_('--value must be provided'))

        path = key.split('.')
        node = siteconfig.settings
        valid_key = True
        key_basename = ''

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
            raise CommandError(_("'%s' is not a valid settings key") % key)

        stored_value = node[key_basename]
        value_type: Type = type(stored_value)

        if value_type not in (str, bytes, int, bool, type(None)):
            raise CommandError(_("Cannot set %s keys") % value_type.__name__)

        try:
            if value_type is bool:
                if value not in ('1', '0', 'True', 'true', 'False', 'false'):
                    raise TypeError
                else:
                    value = (value in ('1', 'True', 'true'))
            elif stored_value is None:
                # Try to guess the type from any specified defaults. Otherwise
                # just assume text.
                defaults = siteconfig.get_defaults()
                value_type = type(defaults.get(key_basename, ''))

            # Special handling for 'null' -> None. If the user really wants an
            # explicit 'null' string, allow them to pass in '\null'.
            if value == 'null':
                norm_value = None
            elif value == '\\null':
                norm_value = 'null'
            else:
                norm_value = value_type(value)
        except TypeError:
            raise CommandError(
                _("'%(value)s' is not a valid %(type)s") % {
                    'value': value,
                    'type': value_type.__name__,
                })

        self.stdout.write(_("Setting '%(key)s' to %(value)s") % {
            'key': key,
            'value': norm_value
        })
        node[key_basename] = norm_value
        siteconfig.save()
