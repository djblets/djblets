from django_evolution.mutations import RenameAppLabel


MUTATIONS = [
    RenameAppLabel('privacy', 'djblets_privacy', legacy_app_label='privacy'),
]
