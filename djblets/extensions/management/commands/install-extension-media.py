from __future__ import unicode_literals

from itertools import chain
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from djblets.extensions.errors import (InstallExtensionError,
                                       InvalidExtensionError)
from djblets.extensions.manager import get_extension_managers


class Command(BaseCommand):
    """Install the extension media.

    This command will install the extension media for either a specific
    extension (specified with the ``--extension-id`` flag) or all installed
    extensions. Installation of the media can be forced (i.e., no version
    checking will be done.
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--extension-id',
            dest='extension_id',
            default=None,
            help=_('An optional extension id')),
        make_option(
            '--force',
            dest='force',
            action='store_true',
            default=False,
            help=_('Force installation of extension media.')),
    )

    def handle(self, *args, **options):
        managers = get_extension_managers()

        force_install = options['force']

        if options['extension_id']:
            extensions = [self._find_extension(options['extension_id'],
                                               managers)]
        else:
            extensions = chain(
                (extension, manager)
                for manager in managers
                for extension in manager.get_enabled_extensions()
            )

        for extension, manager in extensions:
            try:
                manager.install_extension_media(extension, force_install)
            except InstallExtensionError as e:
                raise CommandError('Could not install extension media: %s'
                                   % e)

    def _find_extension(self, extension_id, managers):
        """Find an extension with the given ID in the managers.

        Args:
            extension_id (unicode):
                The extension's ID.

            managers (list):
                A list of :py:class:`~django.extensions.extension.Extension`
                classes (not instances).

        Returns:
            type:
            The specific :py:class:`~django.extensions.extension.Extension`
            class.
        """
        for manager in managers:
            try:
                return manager.get_enabled_extension(extension_id), manager
            except InvalidExtensionError:
                pass

        raise CommandError('No such extension: %s' % extension_id)
