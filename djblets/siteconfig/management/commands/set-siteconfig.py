"""Management command for setting site configuration."""

from __future__ import annotations

import copy
import difflib
import json
import sys
from typing import Any, TYPE_CHECKING

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from djblets.siteconfig.models import SiteConfiguration
from djblets.util.json_utils import json_merge_patch, json_patch

if TYPE_CHECKING:
    from argparse import ArgumentParser

    from djblets.siteconfig.models import (SiteConfigurationSettings,
                                           SiteConfigurationSettingsValue)


class Command(BaseCommand):
    """Sets a setting in the site configuration.

    Settings can be set using one of the following sets of options:

    :option:`--key` / :option:`--value`:
        This enables the caller to set a new value for an existing key.
        The provided key is a dot-separated path within a dictionary of
        the key to set.

        This does not allow for creating new keys.

    :option:`--json-patch`:
        This allows for setting keys to new values using the
        `JSON Patch <https://jsonpatch.com>`_ format. This can be used to
        modify existing settings, create new settings, or delete settings
        by specifying a list of operations to perform on the settings.

        .. note::

           This can be very destructive if not used correctly. Please use
           :command:`list-siteconfig` to back up your settings first.

        Version Added:
            5.2

    :option:`--json-merge-patch`:
        This allows for setting keys to new values using the
        :rfc:`JSON Merge Patch <7396>`_ format. Like JSON Patch, this can be
        used to modify existing settings, create new settings, or delete
        settings, but is done by providing a new JSON document of settings
        that can be merged into the existing document.

        .. note::

           This can be very destructive if not used correctly. Please use
           :command:`list-siteconfig` to back up your settings first.

        Version Added:
            5.2
    """

    def add_arguments(
        self,
        parser: ArgumentParser,
    ) -> None:
        """Add arguments to the command.

        Args:
            parser (object):
                The argument parser to add to.
        """
        parser.add_argument(
            '--key',
            action='store',
            dest='key',
            help=_('The existing key to modify (dot-separated).'))

        parser.add_argument(
            '--value',
            action='store',
            dest='value',
            help=_('The value to store.'))

        parser.add_argument(
            '--json-patch',
            action='store',
            dest='json_patch',
            help=_(
                'The JSON Patch to apply to settings. See '
                'https://jsonpatch.com. Use --json-patch=- to read a patch '
                'from standard input.'
            ))

        parser.add_argument(
            '--json-merge-patch',
            action='store',
            dest='json_merge_patch',
            help=_(
                'The JSON Merge Patch to apply to settings. See '
                'https://datatracker.ietf.org/doc/html/rfc7396. Use '
                '--json-merge-patch=- to read a patch from standard input.'
            ))

        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help=_(
                "Simulate applying the patch or changing a key. The results "
                "will be shown so you can make sure the changes are "
                "correct."
            ))

        parser.add_argument(
            '-y',
            '--confirm',
            action='store_true',
            dest='confirm',
            help=_(
                "Apply a patch without asking for confirmation. Please "
                "note that this can be dangerous if you haven't tested the "
                "patch first."
            ))

    def handle(self, *args, **options) -> None:
        """Handle the set-siteconfig request.

        Args:
            *args (tuple):
                Positional arguments passed to the commad.

            **options (dict):
                Options passed to the command.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        confirm = options['confirm']
        dry_run = options['dry_run']
        merge_patch_json = options['json_merge_patch']
        patch_json = options['json_patch']
        patching = merge_patch_json or patch_json
        needs_confirm = patching

        if patching:
            if merge_patch_json:
                # This is a JSON Merge Patch. Load it and apply to the
                # siteconfig settings.
                patch = self._load_patch(merge_patch_json,
                                         expected_type=dict)
                new_settings = json_merge_patch(siteconfig.settings, patch)
            elif patch_json:
                # This is a JSON Patch. Load it and apply to the siteconfig
                # settings.
                patch = self._load_patch(patch_json,
                                         expected_type=list)
                new_settings = json_patch(siteconfig.settings, patch)
            else:
                assert False, 'Not reached'
        else:
            # This is a simple key/value. Set it in place of an existing key.
            key = options['key']
            value = options['value']

            if key is None:
                raise CommandError(_('--key must be provided'))

            if value is None:
                raise CommandError(_('--value must be provided'))

            new_settings = copy.deepcopy(siteconfig.settings)
            self._set_siteconfig_value(siteconfig=siteconfig,
                                       new_settings=new_settings,
                                       key=key,
                                       value=value)

        # Show the differences between the settings.
        old_settings_json = json.dumps(siteconfig.settings,
                                       indent=2,
                                       sort_keys=True)
        settings_json = json.dumps(new_settings,
                                   indent=2,
                                   sort_keys=True)

        result = list(difflib.unified_diff(
            old_settings_json.splitlines(keepends=True),
            settings_json.splitlines(keepends=True),
            fromfile='settings',
            tofile='settings'))

        if not result:
            self.stdout.write(_(
                'No settings were changed.\n'
            ))
            return

        if dry_run:
            self.stdout.write(_(
                'The following changes would be made (but --dry-run was '
                'passed):\n'
            ))
        else:
            self.stdout.write(_('The following changes will be made:\n'))

        self.stdout.write('\n')

        for line in result:
            self.stdout.write(line)

        self.stdout.write('\n')

        if not new_settings:
            raise CommandError(_(
                'The resulting settings are empty! Cowardly refusing to save.'
            ))

        # Determine whether to apply changes or prompt for confirmation.
        confirmed = (
            not dry_run and
            (not needs_confirm or
             confirm or
             (input(_(
                 'Do you want to apply these changes? [y/N] '
             )).lower() in ('y', 'yes')))
        )

        if confirmed:
            self.stdout.write('The changes have been saved.\n')
            siteconfig.settings = new_settings
            siteconfig.save(update_fields=('settings',))
        else:
            self.stdout.write('No changes have been saved.\n')

        siteconfig.save(update_fields=('settings',))

    def _load_patch(
        self,
        patch: str,
        *,
        expected_type: type,
    ) -> Any:
        """Load and validate a patch.

        Version Changed:
            5.2

        Args:
            patch (str):
                The patch to load.

                If this is "-", then the patch will be loaded from standard
                input.

            expected_type (type):
                The expected data type to load from the patch.

        Returns:
            object:
            The loaded patch.

        Raises:
            django.core.management.base.CommandError:
                There was an error loading or validating the patch.
        """
        if patch == '-':
            # Read the patch from STDIN.
            patch = sys.stdin.read()

        patch = patch.strip()

        try:
            norm_patch = json.loads(patch)
        except Exception as e:
            raise CommandError(_('Invalid patch provided: %s') % e)

        if not norm_patch:
            raise CommandError(_('No patch was provided.'))

        if not isinstance(norm_patch, expected_type):
            raise CommandError(_('Invalid patch provided. Must be a %s.')
                               % type(norm_patch).__name__)

        return norm_patch

    def _set_siteconfig_value(
        self,
        *,
        siteconfig: SiteConfiguration,
        new_settings: SiteConfigurationSettings,
        key: str,
        value: str,
    ) -> None:
        """Set a value for an existing key in the site configuration.

        This takes a dot-separated key path for an existing key in the
        site configuration settings and gives it a new value. The value is
        parsed based on the value type that exists in settings.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The current site configuration, used for accessing defaults.

            new_settings (dict):
                The settings dictionary to modify.

            key (str):
                The dot-separated path to the key to set.

            value (str):
                The serialized value to parse and set on the key.

        Raises:
            django.core.management.base.CommandError:
                There was an error finding or setting the key, or validating
                the value.
        """
        path = key.split('.')
        node: SiteConfigurationSettingsValue = new_settings
        valid_key: bool = True
        key_basename: str = ''

        for item in path[:-1]:
            if not isinstance(node, dict):
                valid_key = False
                break

            try:
                node = node[item]
            except KeyError:
                valid_key = False
                break

        if valid_key:
            assert isinstance(node, dict)

            key_basename = path[-1]

            if key_basename not in node:
                valid_key = False

        if not valid_key:
            raise CommandError(_("'%s' is not a valid settings key") % key)

        # We already know this is a dict, but satisfy the type checker.
        assert isinstance(node, dict)

        stored_value = node[key_basename]
        value_type: type[SiteConfigurationSettingsValue] = type(stored_value)
        norm_value: SiteConfigurationSettingsValue = value

        if value_type not in (str, bytes, int, bool, type(None)):
            raise CommandError(_("Cannot set %s keys") % value_type.__name__)

        try:
            if value_type is bool:
                if value not in ('1', '0', 'True', 'true', 'False', 'false'):
                    raise TypeError
                else:
                    norm_value = (value in ('1', 'True', 'true'))
            elif stored_value is None:
                # Try to guess the type from any specified defaults. Otherwise
                # just assume text.
                defaults = siteconfig.get_defaults()
                value_type = type(defaults.get(key_basename, ''))

            # Special handling for 'null' -> None. If the user really wants an
            # explicit 'null' string, allow them to pass in '\null'.
            if norm_value == 'null':
                norm_value = None
            elif value == '\\null':
                norm_value = 'null'
            else:
                norm_value = value_type(value)  # type: ignore
        except TypeError:
            raise CommandError(
                _("'%(value)s' is not a valid %(type)s") % {
                    'value': value,
                    'type': value_type.__name__,
                })

        node[key_basename] = norm_value
