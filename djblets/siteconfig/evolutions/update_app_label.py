from __future__ import unicode_literals

from django_evolution.mutations import RenameAppLabel


MUTATIONS = [
    RenameAppLabel('siteconfig', 'djblets_siteconfig',
                   legacy_app_label='siteconfig'),
]
