import os

DEBUG = True
PRODUCTION = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'djblets_test.db',
    }
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

USE_TZ = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
STATIC_ROOT = os.path.abspath(os.path.join(__file__, '..', 'static'))
MEDIA_ROOT = os.path.abspath(os.path.join(__file__, '..', 'media'))

MEDIA_URL = '/media/'

# URL that handles the media served from STATIC_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
STATIC_URL = '/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'af=y9ydd51a0g#bevy0+p#(7ime@m#k)$4$9imoz*!rl97w0j0'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = [
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
]

TEMPLATE_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
]

CONTEXT_PROCESSORS = []

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'OPTIONS': {
            'debug': True,
            'context_processors': CONTEXT_PROCESSORS,
            'loaders': TEMPLATE_LOADERS,
        },
    },
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'djblets.testing.urls'


# Explicitly set TEST_RUNNER to avoid incorrect compatibility check warnings
# from Django 1.7.
TEST_RUNNER = 'djblets.testing.testrunners.TestRunner'

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         "..", "djblets"))


NODE_PATH = os.path.join(base_path, '..', 'node_modules')
os.environ['NODE_PATH'] = NODE_PATH

PIPELINE = {
    'PIPELINE_ENABLED': True,
    'COMPILERS': [
        'djblets.pipeline.compilers.es6.ES6Compiler',
        'djblets.pipeline.compilers.less.LessCompiler',
    ],
    'CSS_COMPRESSOR': None,
    'JS_COMPRESSOR': 'pipeline.compressors.uglifyjs.UglifyJSCompressor',
    'BABEL_BINARY': os.path.join(NODE_PATH, '.bin', 'babel'),
    'BABEL_ARGUMENTS': [
        '--presets', '@babel/preset-env',
        '--plugins', ['dedent', 'django-gettext'],
        '-s', 'true',
    ],
    'LESS_BINARY': os.path.join(NODE_PATH, 'less', 'bin', 'lessc'),
    'LESS_ARGUMENTS': [
        '--no-color',
        '--source-map',
        '--js',
        '--autoprefix',
    ],
    'UGLIFYJS_BINARY': os.path.join(NODE_PATH, 'uglify-js', 'bin', 'uglifyjs'),
}


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'oauth2_provider',
    'pipeline',
]


STATICFILES_DIRS = (
    ('djblets', os.path.join(base_path, 'static', 'djblets')),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'djblets.extensions.staticfiles.ExtensionFinder',
    'pipeline.finders.PipelineFinder',
)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'djblets.pipeline.storage.PipelineStorage',
    },
}


for entry in os.listdir(base_path):
    fullpath = os.path.join(base_path, entry)

    if (os.path.isdir(fullpath) and
        os.path.exists(os.path.join(fullpath, "__init__.py"))):
        INSTALLED_APPS += ["djblets.%s" % entry]


INSTALLED_APPS += ['django_evolution']


OAUTH2_PROVIDER = {
    'DEFAULT_SCOPES': 'root:read',
    'SCOPES': {},
}
