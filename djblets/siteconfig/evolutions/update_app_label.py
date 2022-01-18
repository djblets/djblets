from django_evolution.mutations import RenameAppLabel


MUTATIONS = [
    RenameAppLabel('siteconfig', 'djblets_siteconfig',
                   legacy_app_label='siteconfig'),
]
