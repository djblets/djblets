#
# testing.py -- Some classes useful for unit testing django-based applications
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2007-2010  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import print_function, unicode_literals

import importlib
import inspect
import os
import re
import socket
import sys
import threading
import types
import warnings
from collections import OrderedDict
from contextlib import contextmanager
from importlib import import_module
from unittest.util import safe_repr

try:
    # Python >= 3.4
    from importlib.machinery import ModuleSpec

    try:
        # Python >= 3.5
        from importlib.util import module_from_spec
    except ImportError:
        # Python < 3.5
        module_from_spec = None
except ImportError:
    # Python < 3.4
    ModuleSpec = None
    module_from_spec = None

from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers import basehttp
from django.db import (DatabaseError, DEFAULT_DB_ALIAS, IntegrityError,
                       connections, router)
from django.db.models import Model
from django.template import Node
from django.test import testcases
from django.utils import six

try:
    # Django >= 1.7
    from django.apps import apps
except ImportError:
    # Django < 1.7
    from django.db.models.loading import cache as app_cache, load_app

    apps = None

try:
    from django_evolution.models import Evolution, Version
except ImportError:
    Evolution = None
    Version = None

from djblets.siteconfig.models import SiteConfiguration


class StubNodeList(Node):
    def __init__(self, default_text):
        self.default_text = default_text

    def render(self, context):
        return self.default_text


class StubParser:
    def __init__(self, default_text):
        self.default_text = default_text

    def parse(self, until):
        return StubNodeList(self.default_text)

    def delete_first_token(self):
        pass


class TestCase(testcases.TestCase):
    """Base class for test cases.

    Individual tests on this TestCase can use the :py:func:`add_fixtures`
    decorator to add or replace the fixtures used for the test.
    """
    ws_re = re.compile(r'\s+')

    def __call__(self, *args, **kwargs):
        method = getattr(self, self._testMethodName)
        old_fixtures = getattr(self, 'fixtures', None)

        if hasattr(method, '_fixtures'):
            if (getattr(method, '_replace_fixtures') or
                old_fixtures is None):
                self.fixtures = method._fixtures
            else:
                self.fixtures = old_fixtures + method._fixtures

        super(TestCase, self).__call__(*args, **kwargs)

        self.fixtures = old_fixtures

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc

    @contextmanager
    def siteconfig_settings(self, settings):
        """Temporarily sets siteconfig settings for a test.

        Subclasses should override this if they want to run a method like
        :py:func:`~djblets.siteconfig.django_settings.apply_django_settings`
        before and after each test.

        Args:
            settings (dict):
                The new siteconfig settings to set.

        Context:
            The current site configuration will contain the new settings for
            this test.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        old_settings = {}

        for key, value in six.iteritems(settings):
            old_settings[key] = siteconfig.get(key)
            siteconfig.set(key, value)

        siteconfig.save()

        try:
            yield
        finally:
            for key, value in six.iteritems(old_settings):
                siteconfig.set(key, value)

            siteconfig.save()

    def assertAttrsEqual(self, obj, attrs, msg=None):
        """Assert that attributes on an object match expected values.

        This will compare each attribute defined in ``attrs`` against the
        corresponding attribute on ``obj``. If the attribute value does not
        match, or the attribute is missing, this will assert.

        Args:
            obj (object):
                The object to compare attribute values to.

            attrs (dict):
                A dictionary of expected attribute names and values.

            msg (unicode, optional):
                A custom message to include if there's a failure.

        Raises:
            AssertionError:
                An attribute was not found or the value did not match.
        """
        for key, value in six.iteritems(attrs):
            try:
                attr_value = getattr(obj, key)

                if attr_value != value:
                    raise self.failureException(self._formatMessage(
                        msg,
                        '%s: %s != %s'
                        % (key, safe_repr(attr_value),
                           safe_repr(value))))
            except AttributeError:
                raise self.failureException(self._formatMessage(
                    msg,
                    'Attribute "%s" was not found on %s'
                    % (key, safe_repr(obj))))

    def assertRaisesValidationError(self, expected_messages, *args, **kwargs):
        """Assert that a ValidationError is raised with the given message(s).

        This is a wrapper around :py:meth:`assertRaisesMessage` with a
        :py:class:`ValidationError` that handles converting the expected
        messages into a list (if it isn't already) and then converting that
        into a string representation, which is what
        :py:meth:`assertRaisesMessage` will be checking against.

        Args:
            expected_messages (list or unicode):
                The expected messages as either a list of strings or a
                single string.

            args:
                Additional arguments to pass to :py:meth:`assertRaisesMessage`.

            kwargs:
                Additional keyword arguments to pass to
                :py:meth:`assertRaisesMessage`.
        """
        if isinstance(expected_messages, six.string_types):
            expected_messages = [expected_messages]

        return self.assertRaisesMessage(ValidationError,
                                        repr(expected_messages),
                                        *args,
                                        **kwargs)

    def assertRaisesMessage(self, expected_exception, expected_message,
                            *args, **kwargs):
        """Assert that an exception is raised with a given message.

        This is a replacement for Django's assertRaisesMessage that behaves
        well with a design change in Python 2.7.9/10, without crashing.
        """
        # The difference between this version and Django's is that we're
        # not taking the callable_obj as an argument with a default value and
        # passing it down to assertRaisesRegex. Python 2.7.9/10's
        # implementation defaults callable_obj to a special value, which
        # Django overrides.
        return six.assertRaisesRegex(
            self, expected_exception, re.escape(expected_message),
            *args, **kwargs)

    @contextmanager
    def assertWarns(self, cls=DeprecationWarning, message=None):
        """Assert that a warning is generated with a given message.

        This method only supports code which generates a single warning.
        Tests which make use of code generating multiple warnings will
        need to manually catch their warnings.

        Args:
            cls (type, optional):
                The expected warning type.

            message (unicode, optional):
                The expected error message, if any.

        Context:
            The test to run.
        """
        with warnings.catch_warnings(record=True) as w:
            # Some warnings such as DeprecationWarning are filtered by
            # default, stop filtering them.
            warnings.simplefilter('always')
            self.assertEqual(len(w), 0)

            yield

            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, cls))

            if message is not None:
                self.assertEqual(message, six.text_type(w[-1].message))

    @contextmanager
    def assertNoWarnings(self):
        """Assert that a warning is not generated.

        Context:
            The test to run.
        """
        with warnings.catch_warnings(record=True) as w:
            # Some warnings such as DeprecationWarning are filtered by
            # default, stop filtering them.
            warnings.simplefilter('always')
            self.assertEqual(len(w), 0)

            yield

            self.assertEqual(len(w), 0)


class TestModelsLoaderMixin(object):
    """Allows unit test modules to provide models to test against.

    This allows a unit test file to provide models that will be synced to the
    database and flushed after tests. These can be tested against in any unit
    tests.

    Typically, Django requires any test directories to be pre-added to
    INSTALLED_APPS, and a models.py made available (in Django < 1.7), in
    order for models to be created in the test database.

    This mixin works around this by dynamically adding the module to
    INSTALLED_APPS and forcing the database to be synced. It also will
    generate a fake 'models' module to satisfy Django's requirement, if one
    doesn't already exist.

    By default, this will assume that the test class's module is the one that
    should be added to INSTALLED_APPS. This can be changed by overriding
    :py:attr:`tests_app`.
    """
    tests_app = None

    @classmethod
    def setUpClass(cls):
        cls._tests_loader_models_mod = None

        if not cls.tests_app:
            cls.tests_app = cls.__module__

        models_mod_name = '%s.models' % cls.tests_app

        try:
            models_mod = import_module(models_mod_name)
        except ImportError:
            # Set up a 'models' module, containing any models local to the
            # module that this TestCase is in.
            if ModuleSpec:
                # Python >= 3.4
                #
                # It's not enough to simply create a module type. We need to
                # create a basic spec, and then we need to have the module
                # system create a module from it. There's a handy public
                # function to do this on Python 3.5, but Python 3.4 lacks a
                # public function. Fortunately, it's easy to call a private
                # one.
                spec = ModuleSpec(name=models_mod_name,
                                  loader=None)

                if module_from_spec:
                    # Python >= 3.5
                    models_mod = module_from_spec(spec)
                else:
                    # Python == 3.4
                    models_mod = \
                        importlib._bootstrap._SpecMethods(spec).create()

                assert models_mod
            else:
                # Python < 3.4
                models_mod = types.ModuleType(str(models_mod_name))

                # Django needs a value here. Doesn't matter what it is.
                models_mod.__file__ = ''

            # Transfer all the models over into this new module.
            module_name = cls.__module__
            test_module = sys.modules[module_name]

            for key, value in six.iteritems(test_module.__dict__):
                if (inspect.isclass(value) and
                    issubclass(value, Model) and
                    value.__module__ == module_name):
                    models_mod.__dict__[key] = value

        cls._tests_loader_models_mod = models_mod

        if models_mod:
            sys.modules[models_mod.__name__] = models_mod

        cls._models_loader_old_settings = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [
            cls.tests_app,
        ]

        # If Django Evolution is being used, we'll want to clear out any
        # recorded schema information so that it can be generated from
        # scratch when we set up the database.
        if (Evolution is not None and
            Version is not None and
            getattr(settings, 'DJANGO_EVOLUTION_ENABLED', True)):
            Version.objects.all().delete()
            Evolution.objects.all().delete()

        if apps:
            # Push the new set of installed apps, and begin registering
            # each of the models associated with the tests.
            apps.set_installed_apps(settings.INSTALLED_APPS)
            app_config = apps.get_containing_app_config(cls.tests_app)

            if models_mod:
                app_label = app_config.label

                for key, value in six.iteritems(models_mod.__dict__):
                    if inspect.isclass(value) and issubclass(value, Model):
                        # The model was likely registered under another app,
                        # so we need to remove the old one and add the new
                        # one.
                        try:
                            del apps.all_models[value._meta.app_label][
                                value._meta.model_name]
                        except KeyError:
                            pass

                        value._meta.app_label = app_label
                        apps.register_model(app_label, value)

            call_command('migrate', run_syncdb=True, verbosity=0,
                         interactive=False)
        else:
            load_app(cls.tests_app)
            call_command('syncdb', verbosity=0, interactive=False)

        super(TestModelsLoaderMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestModelsLoaderMixin, cls).tearDownClass()

        call_command('flush', verbosity=0, interactive=False)

        settings.INSTALLED_APPS = cls._models_loader_old_settings

        # If we added a fake 'models' module to sys.modules, remove it.
        models_mod = cls._tests_loader_models_mod

        if models_mod:
            try:
                del sys.modules[models_mod.__name__]
            except KeyError:
                pass

        if apps:
            apps.unset_installed_apps()
            apps.all_models[cls.tests_app].clear()
        else:
            if models_mod:
                del app_cache.app_store[models_mod]

            app_cache._get_models_cache.clear()

        # Set this free so the garbage collector can eat it.
        cls._tests_loader_models_mod = None


class FixturesCompilerMixin(object):
    """Compiles and efficiently loads fixtures into a test suite.

    Unlike Django's standard fixture support, this doesn't re-discover
    and re-deserialize the referenced fixtures every time they're needed.
    Instead, it precompiles the fixtures the first time they're found and
    reuses their objects for future tests.

    However, also unlike Django's, this does not accept compressed or
    non-JSON fixtures.
    """

    _precompiled_fixtures = {}
    _fixture_dirs = []

    def _fixture_setup(self):
        """Set up fixtures for unit tests."""
        # Temporarily hide the fixtures, so that the parent class won't
        # do anything with them.
        self._hide_fixtures = True
        super(FixturesCompilerMixin, self)._fixture_setup()
        self._hide_fixtures = False

        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]

        if hasattr(self, 'fixtures'):
            for db in databases:
                self.load_fixtures(self.fixtures, db=db)

    def load_fixtures(self, fixtures, db=DEFAULT_DB_ALIAS):
        """Load fixtures for the current test.

        This is called for every fixture in the test case's ``fixtures``
        list. It can also be called by an individual test to add additional
        fixtures on top of that.

        Args:
            fixtures (list of unicode):
                The list of fixtures to load.

            db (unicode):
                The database name to load fixture data on.
        """
        if not fixtures:
            return

        if db not in self._precompiled_fixtures:
            self._precompiled_fixtures[db] = {}

        for fixture in fixtures:
            if fixture not in self._precompiled_fixtures[db]:
                self._precompile_fixture(fixture, db)

        self._load_fixtures(fixtures, db)

    def _precompile_fixture(self, fixture, db):
        """Precompile a fixture.

        The fixture is loaded and deserialized, and the resulting objects
        are stored for future use.

        Args:
            fixture (unicode):
                The name of the fixture.

            db (unicode):
                The database name to load fixture data on.
        """
        assert db in self._precompiled_fixtures
        assert fixture not in self._precompiled_fixtures[db]

        fixture_path = None

        for fixture_dir in self._get_fixture_dirs():
            fixture_path = os.path.join(fixture_dir, fixture + '.json')

            if os.path.exists(fixture_path):
                break

        try:
            if not fixture_path:
                raise IOError('Fixture path not found')

            with open(fixture_path, 'r') as fp:
                self._precompiled_fixtures[db][fixture] = [
                    obj
                    for obj in serializers.deserialize('json', fp, using=db)
                    if ((hasattr(router, 'allow_syncdb') and
                         router.allow_syncdb(db, obj.object.__class__)) or
                        (hasattr(router, 'allow_migrate_model') and
                         router.allow_migrate_model(db, obj.object)))
                ]
        except IOError as e:
            sys.stderr.write('Unable to load fixture %s: %s\n' % (fixture, e))

    def _get_fixture_dirs(self):
        """Return the list of fixture directories.

        This is computed only once and cached.

        Returns:
            The list of fixture directories.
        """
        if not self._fixture_dirs:
            app_module_paths = []

            for app in self._get_app_model_modules():
                if hasattr(app, '__path__'):
                    # It's a 'models/' subpackage.
                    for path in app.__path__:
                        app_module_paths.append(path)
                else:
                    # It's a models.py module
                    app_module_paths.append(app.__file__)

            all_fixture_dirs = [
                os.path.join(os.path.dirname(path), 'fixtures')
                for path in app_module_paths
            ]

            self._fixture_dirs = [
                fixture_dir
                for fixture_dir in all_fixture_dirs
                if os.path.exists(fixture_dir)
            ]

        return self._fixture_dirs

    def _load_fixtures(self, fixtures, db):
        """Load precompiled fixtures.

        Each precompiled fixture is loaded and then used to populate the
        database.

        Args:
            fixtures (list of unicode):
                The list of fixtures to load.

            db (unicode):
                The database name to load fixture data on.
        """
        table_names = set()
        connection = connections[db]

        with connection.constraint_checks_disabled():
            for fixture in fixtures:
                assert db in self._precompiled_fixtures
                assert fixture in self._precompiled_fixtures[db]
                deserialized_objs = self._precompiled_fixtures[db][fixture]

                to_save = OrderedDict()
                to_save_m2m = []

                # Start off by going through the list of deserialized object
                # information from the fixtures and group them into categories
                # that we'll further filter down later.
                for deserialized_obj in deserialized_objs:
                    obj = deserialized_obj.object

                    table_names.add(obj._meta.db_table)
                    to_save.setdefault(type(obj), []).append(obj)

                    if deserialized_obj.m2m_data:
                        to_save_m2m.append((obj, deserialized_obj.m2m_data))

                # Now we'll break this down into objects we can batch-create
                # and ones we have to update.
                #
                # The database may already have entries for some of these
                # models, particularly if they're being shared across multiple
                # tests for the same suite. In that case, when doing a save()
                # on an object, Django will perform a update-or-create
                # operation, involving an UPDATE statement followed by an
                # INSERT If the UPDATE returned 0 rows.
                #
                # That's wasteful. Instead, we're going to just delete
                # everything matching the deserialized objects' IDs and then
                # bulk-create new entries.
                try:
                    for model_cls, objs in six.iteritems(to_save):
                        obj_ids = [
                            _obj.pk
                            for _obj in objs
                            if _obj.pk
                        ]

                        if obj_ids:
                            model_cls.objects.filter(pk__in=obj_ids).delete()

                        model_cls.objects.using(db).bulk_create(objs)
                except (DatabaseError, IntegrityError) as e:
                    meta = model_cls._meta
                    sys.stderr.write(
                        'Could not load %s.%s from fixture "%s": %s\n'
                        % (meta.app_label,
                           meta.object_name,
                           fixture,
                           e))
                    raise

                # Now save any Many-to-Many field relations.
                #
                # Note that we're not assigning the values to the
                # ManyToManyField attribute. Instead, we're getting the add()
                # method and calling that. We can trust that the relations are
                # empty (since we've newly-created the object), so we don't
                # need to clear the old list first.
                for obj, m2m_data in to_save_m2m:
                    try:
                        for m2m_attr, m2m_objs in six.iteritems(m2m_data):
                            getattr(obj, m2m_attr).add(*m2m_objs)
                    except (DatabaseError, IntegrityError) as e:
                        meta = obj._meta
                        sys.stderr.write(
                            'Could not load Many-to-Many entries for %s.%s '
                            '(pk=%s) in fixture "%s": %s\n'
                            % (meta.app_label,
                               meta.object_name,
                               obj.pk,
                               fixture,
                               e))
                        raise

        # We disabled constraints above, so check now.
        connection.check_constraints(table_names=sorted(table_names))

    def _get_app_model_modules(self):
        """Return the entire list of registered Django app models modules.

        This is an internal utility function that's used to provide
        compatibility with all supported versions of Django.

        Returns:
            list:
            The list of Django applications.
        """
        if apps:
            return [
                app.models_module
                for app in apps.get_app_configs()
                if app.models_module
            ]
        else:
            return app_cache.get_apps()

    def __getattribute__(self, name):
        if name == 'fixtures' and self.__dict__.get('_hide_fixtures'):
            raise AttributeError

        return super(FixturesCompilerMixin, self).__getattribute__(name)


class TagTest(TestCase):
    """Base testing setup for custom template tags"""

    def setUp(self):
        self.parser = StubParser(self.getContentText())

    def getContentText(self):
        return "content"


# The following is all based on the code at
# http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py,
# which is based on the changes submitted for Django in ticket 2879
# (http://code.djangoproject.com/ticket/2879)
#
# A lot of this can go away when/if this patch is committed to Django.

# Code from django_live_server_r8458.diff
#     @ http://code.djangoproject.com/ticket/2879#comment:41
# Editing to monkey patch django rather than be in trunk

class StoppableWSGIServer(basehttp.WSGIServer):
    """
    WSGIServer with short timeout, so that server thread can stop this server.
    """
    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class WSGIRequestHandler(basehttp.WSGIRequestHandler):
    """A custom WSGIRequestHandler that logs all output to stdout.

    Normally, WSGIRequestHandler will color-code messages and log them
    to stderr. It also filters out admin and favicon.ico requests. We don't
    need any of this, and certainly don't want it in stderr, as we'd like
    to only show it on failure.
    """
    def log_message(self, format, *args):
        print(format % args)


class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """
        Sets up test server and database and loops over handling http requests.
        """
        try:
            handler = basehttp.AdminMediaHandler(WSGIHandler())
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address,
                                        WSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except basehttp.WSGIServerException as e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        from django.conf import settings

        if hasattr(settings, 'DATABASES'):
            db_engine = settings.DATABASES['default']['ENGINE']
            test_db_name = settings.DATABASES['default']['TEST_NAME']
        else:
            db_engine = settings.DATABASE_ENGINE
            test_db_name = settings.TEST_DATABASE_NAME

        if (db_engine.endswith('sqlite3') and
            (not test_db_name or test_db_name == ':memory:')):
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                testcases.call_command('loaddata', verbosity=0, *self.fixtures)

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)
