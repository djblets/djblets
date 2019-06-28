from __future__ import unicode_literals

from django_evolution.mutations import RenameAppLabel


MUTATIONS = [
    RenameAppLabel('privacy', 'djblets_privacy', legacy_app_label='privacy'),
]
