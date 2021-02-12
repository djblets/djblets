"""Unit tests for djblets.pipeline.compilers.less.LessCompiler."""

from __future__ import unicode_literals

import os
import shutil
import tempfile

import kgb

from djblets.pipeline.compilers.less import LessCompiler
from djblets.testing.testcases import TestCase


class LessCompilerTests(kgb.SpyAgency, TestCase):
    """Unit tests for djblets.pipeline.compilers.less.LessCompiler."""

    @classmethod
    def setUpClass(cls):
        super(LessCompilerTests, cls).setUpClass()

        cls.compiler = LessCompiler(verbose=True,
                                    storage=None)

        tempdir = tempfile.mkdtemp(prefix='djblets-tests.')
        cls.tempdir = tempdir

        cls.main_less = os.path.join(tempdir, 'main.less')
        cls.dep1_less = os.path.join(tempdir, 'dep1.less')
        cls.dep2_less = os.path.join(tempdir, 'dep2.less')
        cls.dep3_less = os.path.join(tempdir, 'dep3.less')
        cls.main_css = os.path.join(tempdir, 'main.css')
        cls.dep3_css = os.path.join(tempdir, 'dep3.css')
        cls.dep_filenames = [
            cls.dep1_less,
            cls.dep2_less,
            cls.dep3_less,
        ]
        cls.main_filenames = [cls.main_less] + cls.dep_filenames
        cls.all_filenames = cls.main_filenames + [cls.main_css]

        with open(cls.main_less, 'w') as fp:
            fp.write('@import (reference) "dep1.less";\n')
            fp.write('@import (reference) "dep2.less";\n')

        with open(cls.dep1_less, 'w') as fp:
            fp.write('@abc: 123;\n')

        with open(cls.dep2_less, 'w') as fp:
            fp.write('@import (reference) "dep3.less";\n')

        with open(cls.dep3_less, 'w') as fp:
            fp.write('.foo() {}\n')

        with open(cls.main_css, 'w') as fp:
            fp.write('.foo() {}\n')

    @classmethod
    def tearDownClass(cls):
        super(LessCompilerTests, cls).tearDownClass()

        try:
            shutil.rmtree(cls.tempdir)
        except Exception:
            pass

        cls.compiler = None

    def tearDown(self):
        super(LessCompilerTests, self).tearDown()

        self.compiler.clear_caches()

        mtime = os.path.getmtime(self.main_css)

        for filename in self.main_filenames:
            os.utime(filename, (mtime, mtime))

    def test_is_outdated_with_up_to_date(self):
        """Testing LessCompiler.is_outdated with up-to-date files"""
        compiler = self.compiler
        main_less = self.main_less
        main_css = self.main_css

        getmtime_spy = self.spy_on(os.path.getmtime)
        get_import_files_spy = self.spy_on(compiler._get_import_files)

        self.assertFalse(compiler.is_outdated(main_less, main_css))
        self.assertEqual(
            compiler._import_files_cache,
            {
                main_less: set(self.dep_filenames),
            })

        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyCallCount(getmtime_spy, 5)

        for filename in self.all_filenames:
            self.assertSpyCalledWith(getmtime_spy, filename)

        self.assertSpyCallCount(get_import_files_spy, 1)
        self.assertSpyCalledWith(get_import_files_spy, main_less)

        # Make sure everything stayed cached, since nothing was invalidated.
        getmtime_spy.reset_calls()
        get_import_files_spy.reset_calls()

        self.assertFalse(compiler.is_outdated(main_less, main_css))
        self.assertEqual(
            compiler._import_files_cache,
            {
                main_less: set(self.dep_filenames),
            })

        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyNotCalled(getmtime_spy)
        self.assertSpyNotCalled(get_import_files_spy)

    def test_is_outdated_with_outdated_src_file(self):
        """Testing LessCompiler.is_outdated with outdated source file"""
        compiler = self.compiler
        main_less = self.main_less
        main_css = self.main_css

        getmtime_spy = self.spy_on(os.path.getmtime)
        get_import_files_spy = self.spy_on(compiler._get_import_files)

        self.assertFalse(compiler.is_outdated(main_less, main_css))
        self.assertEqual(
            compiler._import_files_cache,
            {
                main_less: set(self.dep_filenames),
            })

        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyCallCount(getmtime_spy, 5)

        for filename in self.all_filenames:
            self.assertSpyCalledWith(getmtime_spy, filename)

        self.assertSpyCallCount(get_import_files_spy, 1)
        self.assertSpyCalledWith(get_import_files_spy, main_less)

        # Update the timestamp and try again.
        self._touch(main_less)

        getmtime_spy.reset_calls()
        get_import_files_spy.reset_calls()

        self.assertTrue(compiler.is_outdated(main_less, main_css))
        self.assertEqual(compiler._import_files_cache, {})
        self.assertEqual(set(compiler._mtime_cache), {main_less, main_css})

        self.assertSpyCallCount(getmtime_spy, 2)
        self.assertSpyCalledWith(getmtime_spy, main_less)
        self.assertSpyCalledWith(getmtime_spy, main_css)

        self.assertSpyNotCalled(get_import_files_spy)

    def test_is_outdated_with_no_dest_file(self):
        """Testing LessCompiler.is_outdated with missing destination file"""
        compiler = self.compiler
        dep3_less = self.dep3_less
        dep3_css = self.dep3_css

        getmtime_spy = self.spy_on(os.path.getmtime)
        get_import_files_spy = self.spy_on(compiler._get_import_files)

        self.assertFalse(os.path.exists(dep3_css))
        self.assertTrue(compiler.is_outdated(dep3_less, dep3_css))
        self.assertEqual(compiler._import_files_cache, {})

        self.assertEqual(set(compiler._mtime_cache), {dep3_css})
        self.assertSpyCallCount(getmtime_spy, 1)
        self.assertSpyCalledWith(getmtime_spy, dep3_css)

        self.assertSpyNotCalled(get_import_files_spy)

    def test_is_outdated_with_outdated_dep(self):
        """Testing LessCompiler.is_outdated with outdated import file"""
        compiler = self.compiler
        main_less = self.main_less
        main_css = self.main_css

        getmtime_spy = self.spy_on(os.path.getmtime)
        get_import_files_spy = self.spy_on(compiler._get_import_files)

        self.assertFalse(compiler.is_outdated(main_less, main_css))
        self.assertEqual(
            compiler._import_files_cache,
            {
                main_less: set(self.dep_filenames),
            })

        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyCallCount(getmtime_spy, 5)

        for filename in self.all_filenames:
            self.assertSpyCalledWith(getmtime_spy, filename)

        self.assertSpyCallCount(get_import_files_spy, 1)
        self.assertSpyCalledWith(get_import_files_spy, main_less)

        # Update the timestamp and try again.
        self._touch(self.dep3_less)

        getmtime_spy.reset_calls()
        get_import_files_spy.reset_calls()

        self.assertTrue(compiler.is_outdated(main_less, main_css))
        self.assertEqual(compiler._import_files_cache, {})
        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyCallCount(getmtime_spy, 5)

        for filename in self.all_filenames:
            self.assertSpyCalledWith(getmtime_spy, filename)

        self.assertSpyCallCount(get_import_files_spy, 1)
        self.assertSpyCalledWith(get_import_files_spy, main_less)

        # Make sure mtimes stay cached. We will have to re-import again due
        # to a dependency cache being invalidated.
        getmtime_spy.reset_calls()
        get_import_files_spy.reset_calls()

        self.assertTrue(compiler.is_outdated(main_less, main_css))
        self.assertEqual(compiler._import_files_cache, {})
        self.assertEqual(set(compiler._mtime_cache),
                         set(self.all_filenames))

        self.assertSpyNotCalled(getmtime_spy)

        self.assertSpyCallCount(get_import_files_spy, 1)
        self.assertSpyCalledWith(get_import_files_spy, main_less)

    def _touch(self, filename):
        """Update the timestamp on a file.

        Args:
            filename (unicode):
                The filename of the file to update.
        """
        os.utime(filename, None)
        self.compiler.clear_caches()
