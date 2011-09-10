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

import socket
import threading

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers import basehttp
from django.template import Node
from django.test import testcases
from nose import SkipTest


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
    def __call__(self, *args, **kwargs):
        method = getattr(self, self._testMethodName)
        old_fixtures = getattr(self, 'fixtures', [])

        if hasattr(method, '_fixtures'):
            if getattr(method, '_replace_fixtures'):
                self.fixtures = method._fixtures
            else:
                self.fixtures = old_fixtures + method._fixtures

        super(TestCase, self).__call__(*args, **kwargs)

        if old_fixtures:
            self.fixtures = old_fixtures


class TagTest(TestCase):
    """Base testing setup for custom template tags"""

    def setUp(self):
        self.parser = StubParser(self.getContentText())

    def getContentText(self):
        return "content"


class SeleniumUnitTest(TestCase):
    """A unit test that makes use of the Selenium browser automation tool.

    SeleniumUnitTest makes it easy to write unit tests that make use of
    Selenium, a browser automation tool, in order to test functionality
    from the point of view of the user.

    This will set up a single-threaded live dev server for testing, by
    default on port 8002. This port can be changed by overriding
    ``server_port`` in the subclass.

    This will attempt to re-use both this dev server and the Selenium browser
    session for all subclasses of SeleniumUnitTest, but this can be changed
    by overriding ``reuse_selenium`` and ``reuse_live_server`` in the
    subclass.

    Selenium unit tests support the following variables in the project's
    settings file:

      * ``SELENIUM_HOST`` - The host containing the Selenium server and
                            browser. Defaults to ``localhost``.
      * ``SELENIUM_PORT`` - The port for the Selenium server. Defaults to
                            ``4444``.
      * ``SELENIUM_BROWSER_COMMAND`` - The Selenium browser command
                                       representing the browser to use.
                                       Defaults to ``*firefox``.
      * ``SELENIUM_LIVE_SERVER_ADDRESS`` - The address for the live dev server.
                                           Defaults to ``0.0.0.0``.

    If the server cannot be contacted, this will raise ``SkipTest``.
    """

    # Configuration
    server_port = 8002
    reuse_selenium = True
    reuse_live_server = True

    # State
    live_server_running = False
    server_address = None
    test_url = None
    selenium = None
    server_thread = None

    def setUp(self):
        if (not self.reuse_live_server or
            not SeleniumUnitTest.live_server_running):
            SeleniumUnitTest.start_live_server()

        if not self.reuse_selenium or SeleniumUnitTest.selenium is None:
            SeleniumUnitTest.start_selenium()

    def tearDown(self):
        if not self.reuse_selenium:
            SeleniumUnitTest.stop_selenium()

        if not self.reuse_live_server:
            SeleniumUnitTest.stop_live_server()

    @classmethod
    def tearDownAll(cls):
        SeleniumUnitTest.stop_selenium()
        SeleniumUnitTest.stop_live_server()

    @classmethod
    def start_selenium(cls):
        from selenium import selenium

        cls.selenium = selenium(
            getattr(settings, 'SELENIUM_HOST', 'localhost'),
            getattr(settings, 'SELENIUM_PORT', 4444),
            getattr(settings, 'SELENIUM_BROWSER_COMMAND', '*firefox'),
            cls.test_url)

        try:
            cls.selenium.start()
        except Exception, e:
            cls.selenium = None
            raise SkipTest(e)

    @classmethod
    def stop_selenium(cls):
        if cls.selenium:
            cls.selenium.stop()
            cls.selenium = None

    @classmethod
    def start_live_server(cls):
        """Creates a live test server object (instance of WSGIServer)."""
        if not cls.server_address:
            cls.server_address = getattr(settings,
                                         'SELENIUM_LIVE_SERVER_ADDRESS',
                                         '0.0.0.0')
            cls.test_url = 'http://%s:%d%s' % (
                cls.server_address,
                cls.server_port,
                getattr(settings, 'SITE_ROOT', ''))

        cls.server_thread = TestServerThread(cls.server_address,
                                             cls.server_port)
        cls.server_thread.start()
        cls.server_thread.started.wait()

        if cls.server_thread.error:
            raise cls.server_thread.error

        cls.live_server_running = True

    @classmethod
    def stop_live_server(cls):
        if cls.server_thread:
            cls.server_thread.join()

        cls.live_server_running = False


# The following is all based on the code at
# http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py,
# which is based on the changes submitted for Django in ticket 2879
# (http://code.djangoproject.com/ticket/2879)
#
# A lot of this can go away when/if this patch is committed to Django.

# Code from django_live_server_r8458.diff @  http://code.djangoproject.com/ticket/2879#comment:41
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
        print format % args


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
        except basehttp.WSGIServerException, e:
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
