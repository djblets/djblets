from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import CommandError, NoArgsCommand
from django.utils import six
from django.utils.translation import ugettext as _

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Sets a setting in the site configuration.

    This cannot create new settings. It can only set existing ones.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--key', action='store', dest='key',
                    help=_('The existing key to modify (dot-separated)')),
        make_option('--value', action='store', dest='value',
                    help=_('The value to store')),
    )

    def handle_noargs(self, **options):
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
        value_type = type(stored_value)

        if value_type not in (six.text_type, six.binary_type, int, bool):
            raise CommandError(_("Cannot set %s keys") % value_type.__name__)

        try:
            if value_type is bool:
                if value not in ('1', '0'):
                    raise TypeError
                else:
                    value = (value == '1')

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
