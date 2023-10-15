#!/usr/bin/env python3

from __future__ import print_function, unicode_literals

import json
import os
import subprocess
import sys

from setuptools import Command, find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info
from setuptools.command.test import test

from djblets import get_package_version, VERSION
from djblets.dependencies import (PYTHON_3_MIN_VERSION,
                                  build_dependency_list,
                                  npm_dependencies,
                                  package_dependencies)


# Make sure this is a version of Python we are compatible with. This should
# prevent people on older versions from unintentionally trying to install
# the source tarball, and failing.
pyver = sys.version_info[:2]

if pyver < PYTHON_3_MIN_VERSION:
    sys.stderr.write('This version of Djblets is incompatible with your '
                     'version of Python.\n')
    sys.exit(1)


# NOTE: When updating, make sure you update the classifiers below.
#
# Python end-of-life dates (as of October 2, 2021):
#
# 3.7: June 27, 2023
# 3.8: October 14, 2024
# 3.9: October 5, 2025
#
# See https://endoflife.date/python
SUPPORTED_PYVERS = ['3.8', '3.9', '3.10', '3.11', '3.12']


if '--all-pyvers' in sys.argv:
    new_argv = sys.argv[1:]
    new_argv.remove('--all-pyvers')

    for pyver in SUPPORTED_PYVERS:
        result = os.system(subprocess.list2cmdline(
            ['python%s' % pyver, __file__] + new_argv))

        if result != 0:
            sys.exit(result)

    sys.exit(0)


# We want to use subprocess.check_output to see if certain commands can be run,
# but on Python 2.6 we don't have this. Instead, use subprocess.check_call
# (which will display any results to stdout).
if hasattr(subprocess, 'check_output'):
    check_run = subprocess.check_output
else:
    check_run = subprocess.check_call


class BuildEggInfoCommand(egg_info):
    """Build the egg information for the package.

    If this is called when building a distribution (source, egg, or wheel),
    or when installing the package from source, this will kick off tasks for
    building static media and string localization files.
    """

    def run(self):
        """Build the egg information."""
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

    To speed up subsequent runs, callers can pass ``--no-npm`` to prevent
    installing node.js packages.
    """

    user_options = develop.user_options + [
        (str('no-npm'), None,
         "Don't install packages from npm"),
        (str('use-npm-cache'),
         None,
         'Use npm-cache to install packages'),
        (str('with-doc-deps'),
         None,
         'Install documentation-related dependencies'),
    ]

    boolean_options = develop.boolean_options + [
        str('no-npm'),
        str('use-npm-cache'),
        str('with-doc-deps'),
    ]

    def initialize_options(self):
        """Initialize options for the command."""
        develop.initialize_options(self)

        self.no_npm = None
        self.with_doc_deps = None
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

        try:
            check_run(['node', '--version'])
        except (subprocess.CalledProcessError, OSError):
            try:
                check_run(['nodejs', '--version'])
            except:
                # nodejs wasn't found, which is fine. We want to ignore this.
                pass
            else:
                raise RuntimeError(
                    'Unable to find "node" in the path, but "nodejs" was '
                    'found. You will need to ensure "nodejs" can be run '
                    'by typing "node". You can do this by typing `ln -s '
                    'nodejs node` in the directory containing "nodejs".')

            raise RuntimeError(
                'Unable to find "node" in the path. You will need to '
                'install a modern version of NodeJS and ensure you can '
                'run it by typing "node" on the command line.')

        # Install the dependencies using pip instead of easy_install. This
        # will use wheels instead of legacy eggs.
        self._run_pip(['install', '-e', '.'])
        self._run_pip(['install', '-r', 'dev-requirements.txt'])

        if self.with_doc_deps:
            self._run_pip(['install', '-r', 'doc-requirements.txt'])

        if not self.no_npm:
            # Install node.js dependencies, needed for packaging.
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
        cmd = subprocess.list2cmdline([sys.executable, '-m', 'pip'] + args)
        ret = os.system(cmd)

        if ret != 0:
            raise RuntimeError('Failed to run `%s`' % cmd)


class BuildMediaCommand(Command):
    """Builds static media files for the package.

    This requires first having the node.js dependencies installed.
    """

    user_options = []

    def initialize_options(self):
        """Initialize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def finalize_options(self):
        """Finalize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def run(self):
        """Runs the commands to build the static media files.

        Raises:
            RuntimeError:
                Static media failed to build.
        """
        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-media.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build media files')


class BuildI18nCommand(Command):
    """Builds string localization files."""

    description = 'Compile message catalogs to .mo'
    user_options = []

    def initialize_options(self):
        """Initialize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def finalize_options(self):
        """Finalize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def run(self):
        """Runs the commands to build the string localization files.

        Raises:
            RuntimeError:
                Localization files failed to build.
        """
        # If we are attempting to build on a system without an
        # existing copy of Djblets installed in a reachable
        # location (such as distribution packaging), we need to
        # ensure that the source directory is in the PYTHONPATH
        # or the import of djblets.util.filesystem will fail.
        current_path = os.getenv('PYTHONPATH')

        if current_path:
            os.putenv('PYTHONPATH', '%s:%s' % (current_path, os.getcwd()))
        else:
            os.putenv('PYTHONPATH', os.getcwd())

        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-i18n.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build i18n files')


class FetchPublicSuffixListCommand(Command):
    """Fetches the DNS public suffix list for use in DMARC lookups."""

    description = 'Fetch the DNS public suffix list from publicsuffix.org.'
    user_options = []

    def initialize_options(self):
        """Initialize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def finalize_options(self):
        """Finalize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def run(self):
        """Run the commands to fetch the DNS public suffix list."""
        from publicsuffix import fetch as fetch_public_suffix

        print('Fetching DNS public suffix list...')
        filename = os.path.join('djblets', 'mail', 'public_suffix_list.dat')

        with open(filename, 'w') as fp:
            fp.write(fetch_public_suffix().read().encode('utf-8'))

        print('Public suffix list stored at %s' % filename)


class InstallNodeDependenciesCommand(Command):
    """Installs all node.js dependencies from npm.

    If ``--use-npm-cache`` is passed, this will use :command:`npm-cache`
    to install the packages, which is best for Continuous Integration setups.
    Otherwise, :command:`npm` is used.
    """

    description = \
        'Install the node packages required for building static media.'

    user_options = [
        (str('use-npm-cache'), None, 'Use npm-cache to install packages'),
    ]

    boolean_options = [str('use-npm-cache')]

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
            check_run([npm_command, '--version'])
        except (subprocess.CalledProcessError, OSError):
            raise RuntimeError(
                'Unable to locate %s in the path, which is needed to '
                'install dependencies required to build this package.'
                % npm_command)

        print('Installing node.js modules...')
        result = os.system('%s install' % npm_command)

        if result != 0:
            raise RuntimeError(
                'One or more node.js modules could not be installed.')


# Tell `setup.py tests` how to invoke our test suite.
test.run_tests = lambda *args, **kwargs: os.system('tests/runtests.py')


with open('README.rst', 'r') as fp:
    long_description = fp.read()


PACKAGE_NAME = 'Djblets'

setup(
    name=PACKAGE_NAME,
    version=get_package_version(),
    license='MIT',
    description=(
        'A collection of useful classes and functions for developing '
        'large-scale Django-based web applications.'
    ),
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='Beanbag, Inc.',
    author_email='reviewboard@googlegroups.com',
    url='https://www.reviewboard.org/downloads/djblets/',
    download_url=('https://downloads.reviewboard.org/releases/%s/%s.%s/'
                  % (PACKAGE_NAME, VERSION[0], VERSION[1])),
    packages=find_packages(exclude=['tests']),
    install_requires=build_dependency_list(package_dependencies),
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False,
    test_suite='dummy',
    cmdclass={
        'build_media': BuildMediaCommand,
        'build_i18n': BuildI18nCommand,
        'develop': DevelopCommand,
        'egg_info': BuildEggInfoCommand,
        'fetch_public_suffix_list': FetchPublicSuffixListCommand,
        'install_node_deps': InstallNodeDependenciesCommand,
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
