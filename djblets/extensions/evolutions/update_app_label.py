from __future__ import unicode_literals

from django_evolution.mutations import RenameAppLabel


MUTATIONS = [
    RenameAppLabel('extensions', 'djblets_extensions',
                   legacy_app_label='extensions'),
]
