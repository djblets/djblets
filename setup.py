#!/usr/bin/env python
#
# setup.py -- Installation for djblets
#
# Copyright (C) 2008 Christian Hammond
# Copyright (C) 2007-2008 David Trowbridge
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

import subprocess
import sys
import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from distutils.core import Command
from setuptools.command.egg_info import egg_info
from setuptools.command.test import test

from djblets import django_version, get_package_version, is_release, VERSION


# Make sure this is a version of Python we are compatible with. This should
# prevent people on older versions from unintentionally trying to install
# the source tarball, and failing.
if sys.hexversion < 0x02060000:
    sys.stderr.write('This version of Djblets is incompatible with your '
                     'version of Python.\n')
    sys.exit(1)


class BuildEggInfo(egg_info):
    def run(self):
        if ('sdist' in sys.argv or
            'bdist_egg' in sys.argv or
            'install' in sys.argv):
            self.run_command('build_media')
            self.run_command('build_i18n')

        egg_info.run(self)


class BuildMedia(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-media.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build media files')


class BuildI18n(Command):
    description = 'Compile message catalogs to .mo'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # If we are attempting to build on a system without an
        # existing copy of Djblets installed in a reachable
        # location (such as distribution packaging), we need to
        # ensure that the source directory is in the PYTHONPATH
        # or the import of djblets.util.filesystem will fail.
        current_path = os.getenv("PYTHONPATH")
        if current_path:
            os.putenv("PYTHONPATH", "%s:%s" % (current_path, os.getcwd()))
        else:
            os.putenv("PYTHONPATH", os.getcwd())

        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-i18n.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build i18n files')


def run_tests(*args):
    import os
    os.system("tests/runtests.py")

test.run_tests = run_tests

cmdclasses = {
    'egg_info': BuildEggInfo,
    'build_media': BuildMedia,
    'build_i18n': BuildI18n,
}


PACKAGE_NAME = 'Djblets'

if is_release():
    download_url = 'http://downloads.reviewboard.org/releases/%s/%s.%s/' % \
                   (PACKAGE_NAME, VERSION[0], VERSION[1])
else:
    download_url = 'http://downloads.reviewboard.org/nightlies/'


setup(name=PACKAGE_NAME,
      version=get_package_version(),
      test_suite="dummy",
      license="MIT",
      description="A collection of useful classes and functions for Django",
      packages=find_packages(exclude=["tests"]),
      cmdclass=cmdclasses,
      install_requires=[
          django_version,
          'django-pipeline>=1.3.23,<1.3.9999',
          'feedparser>=5.1.2',
          'pillowfight',
          'pytz',
      ],
      dependency_links=[
          "http://downloads.reviewboard.org/mirror/",
          download_url,
      ],
      include_package_data=True,
      zip_safe=False,
      maintainer="Christian Hammond",
      maintainer_email="christian@beanbaginc.com",
      url="https://www.reviewboard.org/downloads/djblets/",
      download_url=download_url,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Web Environment",
          "Framework :: Django",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Topic :: Software Development",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ])
