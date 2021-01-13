#
# Settings for djblets.
#
# This is meant for internal use only. We use it primarily for building
# static media to bundle with djblets.
#
# This should generally not be used in a project.
from __future__ import unicode_literals

import os

from djblets.pipeline.settings import build_pipeline_settings
from djblets.staticbundles import PIPELINE_JAVASCRIPT, PIPELINE_STYLESHEETS


SECRET_KEY = '47157c7ae957f904ab809d8c5b77e0209221d4c0'

USE_I18N = True

DEBUG = False
DJBLETS_ROOT = os.path.abspath(os.path.dirname(__file__))
HTDOCS_ROOT = os.path.join(DJBLETS_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
STATIC_URL = '/'
LOGIN_LIMIT_RATE = '5/m'

STATICFILES_DIRS = (
    os.path.join(DJBLETS_ROOT, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'


NODE_PATH = os.path.abspath(os.path.join(DJBLETS_ROOT, '..', 'node_modules'))


PIPELINE = build_pipeline_settings(
    pipeline_enabled=not DEBUG or os.getenv('FORCE_BUILD_MEDIA'),
    node_modules_path=NODE_PATH,
    static_root=STATIC_ROOT,
    javascript_bundles=PIPELINE_JAVASCRIPT,
    stylesheet_bundles=PIPELINE_STYLESHEETS,
    validate_paths=DEBUG)


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'djblets.auth',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.feedview',
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
