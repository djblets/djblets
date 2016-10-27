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

import json
import os
import subprocess
import sys
from distutils.core import Command

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info
from setuptools.command.test import test

from djblets import get_package_version, is_release, VERSION
from djblets.dependencies import (build_dependency_list, npm_dependencies,
                                  package_dependencies)


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
            'bdist_wheel' in sys.argv or
            'install' in sys.argv):
            self.run_command('build_media')
            self.run_command('build_i18n')

        egg_info.run(self)


class DevelopCommand(develop):
    """Installs Djblets in developer mode.

    This will install all standard and development dependencies (using Python
    wheels and node.js packages from npm) and add the source tree to the
    Python module search path. That includes updating the versions of pip
    and setuptools on the system.

    To speed up subsequent runs, callers can pass --no-npm to prevent
    installing node.js packages.
    """

    user_options = develop.user_options + [
        ('no-npm', None, "Don't install packages from npm"),
        ('use-npm-cache', None, "Use npm-cache to install packages"),
    ]

    boolean_options = develop.boolean_options + ['no-npm', 'use-npm-cache']

    def initialize_options(self):
        """Initialize options for the command."""
        develop.initialize_options(self)

        self.no_npm = None
        self.use_npm_cache = None

    def install_for_development(self):
        """Install the package for development.

        This takes care of the work of installing all dependencies.
        """
        if self.no_deps:
            # In this case, we don't want to install any of the dependencies
            # below. However, it's really unlikely that a user is going to
            # want to pass --no-deps.
            #
            # Instead, what this really does is give us a way to know we've
            # been called by `pip install -e .`. That will call us with
            # --no-deps, as it's going to actually handle all dependency
            # installation, rather than having easy_install do it.
            develop.install_for_development(self)
            return

        # Install the latest pip and setuptools. Note that the order here
        # matters, as otherwise a stale setuptools can be left behind,
        # causing installation errors.
        self._run_pip(['install', '-U', 'setuptools'])
        self._run_pip(['install', '-U', 'pip'])

        # Install the dependencies using pip instead of easy_install. This
        # will use wheels instead of eggs, which are ideal for our users.
        self._run_pip(['install', '-e', '.'])
        self._run_pip(['install', '-r', 'dev-requirements.txt'])

        if not self.no_npm:
            if self.use_npm_cache:
                self.distribution.command_options['install_node_deps'] = {
                    'use_npm_cache': ('install_node_deps', 1),
                }

            self.run_command('install_node_deps')

    def _run_pip(self, args):
        """Run pip.

        Args:
            args (list):
                Arguments to pass to :command:`pip`.

        Raises:
            RuntimeError:
                The :command:`pip` command returned a non-zero exit code.
        """
        # NOTE: We need to do pip.__main__ to support Python 2.6. This is not
        #       required (but does work) for Python 2.7+.
        cmd = subprocess.list2cmdline([sys.executable, '-m', 'pip.__main__'] +
                                      args)
        ret = os.system(cmd)

        if ret != 0:
            raise RuntimeError('Failed to run `%s`' % cmd)


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


class InstallNodeDependenciesCommand(Command):
    """Install all node.js dependencies from npm.

    If ``--use-npm-cache`` is passed, this will use :command:`npm-cache`
    to install the packages, which is best for Continuous Integration setups.
    Otherwise, :command:`npm` is used.
    """

    description = \
        'Install the node packages required for building static media.'

    user_options = [
        ('use-npm-cache', None, "Use npm-cache to install packages"),
    ]

    boolean_options = ['use-npm-cache']

    def initialize_options(self):
        """Initialize options for the command."""
        self.use_npm_cache = None

    def finalize_options(self):
        """Finalize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def run(self):
        """Run the commands to install packages from npm.

        Raises:
            RuntimeError:
                There was an error finding or invoking the package manager.
        """
        if self.use_npm_cache:
            npm_command = 'npm-cache'
        else:
            npm_command = 'npm'

        try:
            subprocess.check_call([npm_command, '--version'])
        except subprocess.CalledProcessError:
            raise RuntimeError(
                'Unable to locate %s in the path, which is needed to '
                'install dependencies required to build this package.'
                % npm_command)

        with open('package.json', 'w') as fp:
            fp.write(json.dumps(
                {
                    'name': 'djblets',
                    'private': 'true',
                    'devDependencies': {},
                    'dependencies': npm_dependencies,
                },
                indent=2))

        print 'Installing node.js modules...'
        result = os.system('%s install' % npm_command)

        os.unlink('package.json')

        if result != 0:
            raise RuntimeError(
                'One or more node.js modules could not be installed.')


test.run_tests = lambda *args, **kwargs: os.system('tests/runtests.py')

cmdclasses = {
    'develop': DevelopCommand,
    'egg_info': BuildEggInfo,
    'build_media': BuildMedia,
    'build_i18n': BuildI18n,
    'install_node_deps': InstallNodeDependenciesCommand,
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
      install_requires=build_dependency_list(package_dependencies),
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
