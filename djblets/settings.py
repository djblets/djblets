#
# Settings for djblets.
#
# This is meant for internal use only. We use it primarily for building
# static media to bundle with djblets.
#
# This should generally not be used in a project.
from __future__ import unicode_literals

import os

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


NODE_PATH = os.path.join(DJBLETS_ROOT, '..', 'node_modules')
os.environ['NODE_PATH'] = NODE_PATH


PIPELINE = {
    'PIPELINE_ENABLED': not DEBUG or os.getenv('FORCE_BUILD_MEDIA'),
    'COMPILERS': [
        'djblets.pipeline.compilers.es6.ES6Compiler',
        'djblets.pipeline.compilers.less.LessCompiler',
    ],
    'CSS_COMPRESSOR': None,
    'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
    'JAVASCRIPT': PIPELINE_JAVASCRIPT,
    'STYLESHEETS': PIPELINE_STYLESHEETS,
    'BABEL_BINARY': os.path.join(NODE_PATH, 'babel-cli', 'bin', 'babel.js'),
    'BABEL_ARGUMENTS': [
        '--presets', 'env',
        '--plugins', 'dedent,django-gettext',
        '-s', 'true',
    ],
    'LESS_BINARY': os.path.join(NODE_PATH, 'less', 'bin', 'lessc'),
    'LESS_ARGUMENTS': [
        '--include-path=%s' % STATIC_ROOT,
        '--no-color',
        '--source-map',
        '--js',
        '--autoprefix',
    ],
    'UGLIFYJS_BINARY': os.path.join(NODE_PATH, 'uglify-js', 'bin', 'uglifyjs'),
}

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
