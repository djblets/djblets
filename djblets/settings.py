"""Settings for djblets.

This is meant for internal use only. We use it primarily for building
static media to bundle with djblets.

This should generally not be used in a project.
"""

import os

from djblets.pipeline.settings import build_pipeline_settings
from djblets.staticbundles import PIPELINE_JAVASCRIPT, PIPELINE_STYLESHEETS


SECRET_KEY = '47157c7ae957f904ab809d8c5b77e0209221d4c0'

USE_I18N = True

DEBUG = False
PRODUCTION = True
DJBLETS_ROOT = os.path.abspath(os.path.dirname(__file__))
HTDOCS_ROOT = os.path.join(DJBLETS_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
MEDIA_ROOT = os.path.join(HTDOCS_ROOT, 'media')
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
LOGIN_LIMIT_RATE = '5/m'

STATICFILES_DIRS = (
    os.path.join(DJBLETS_ROOT, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'djblets.pipeline.storage.PipelineStorage',
    },
}


NODE_PATH = os.path.abspath(os.path.join(DJBLETS_ROOT, '..', 'node_modules'))


PIPELINE = build_pipeline_settings(
    pipeline_enabled=(
        PRODUCTION or
        not DEBUG or
        (os.getenv('FORCE_BUILD_MEDIA') == '1')),
    node_modules_path=NODE_PATH,
    static_root=STATIC_ROOT,
    javascript_bundles=PIPELINE_JAVASCRIPT,
    stylesheet_bundles=PIPELINE_STYLESHEETS,
    use_rollup=True,
    validate_paths=not PRODUCTION)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'djblets.auth',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.gravatars',
    'djblets.log',
    'djblets.pipeline',
    'djblets.privacy',
    'djblets.siteconfig',
    'djblets.testing',
    'djblets.util',
    'djblets.webapi',
    'django_evolution',
]
