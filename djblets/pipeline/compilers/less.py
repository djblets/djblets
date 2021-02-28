"""A specialization of pipeline's LessCompiler."""

from __future__ import unicode_literals

import logging
import os
import subprocess
from datetime import datetime

from django.utils import six
from django.utils.functional import cached_property
from pipeline.compilers.less import LessCompiler as PipelineLessCompiler
from pipeline.conf import settings as pipeline_settings


class LessCompiler(PipelineLessCompiler):
    """A LESS compiler which doesn't redirect the output.

    Pipeline's LESS compiler outputs to stdout and redirects that output to the
    target file, because of some bug in old versions of lessc. We don't want to
    do that, because it interferes with the generation of sourcemaps.

    To use this, add the path to this class to
    ``settings.PIPELINE['COMPILERS']``.

    Version Changed:
        2.2:
        Added in-memory caching of import lists and file information to
        speed up performance of compilations.
    """

    #: Cache expiration time for the list of outdated timestamp states.
    #:
    #: Version Added:
    #:     2.2
    _MTIME_CACHE_STALE_SECS = 10

    #: Cache mapping files to lists of imported files.
    #:
    #: Version Added:
    #:     2.2
    #:
    #: Type:
    #:     dict
    _import_files_cache = {}

    #: Cache of filenames to mtimes.
    #:
    #: Version Added:
    #:     2.2
    #:
    #: Type:
    #:     dict
    _mtime_cache = {}

    #: The latest updated timestamp for the mtime cache.
    #:
    #: Version Added:
    #:     2.2
    #:
    #: Type:
    #:     datetime.datetime
    _mtime_cache_stamp = None

    @classmethod
    def clear_caches(cls):
        """Clear the caches used for faster compilation."""
        cls._import_files_cache.clear()
        cls._mtime_cache.clear()
        cls._mtime_cache_stamp = None

    @cached_property
    def less_imports_command(self):
        """Command line and arguments for less-imports.js.

        Type:
            unicode
        """
        return [
            os.path.join(os.path.dirname(__file__), 'less-imports.js'),
        ] + list(pipeline_settings.LESS_ARGUMENTS)

    def compile_file(self, infile, outfile, outdated=False, force=False):
        """Compile a given file.

        Args:
            infile (unicode):
                The input filename.

            outfile (unicode):
                The output filename.

            outdated (bool):
                Whether the file is outdated.

            force (bool):
                Whether the compilation should proceed, regardless of whether
                the file is out of date.
        """
        if outdated or force:
            self.execute_command((
                pipeline_settings.LESS_BINARY,
                pipeline_settings.LESS_ARGUMENTS,
                infile,
                outfile
            ))

    def is_outdated(self, infile, outfile):
        """Return whether a given file is outdated.

        This will compare the timestamps of the ``infile`` and ``outfile``, but
        also compare the timestamp of ``outfile`` against any import
        depedencies that exist.

        Args:
            infile (unicode):
                The path to the input file.

            outfile (unicode):
                The path to the output file.

        Returns:
            bool:
            True if the file is out of date and needs to be recompiled.
        """
        # If the file itself is outdated, or we want to always treat all files
        # as outdated, don't bother to dive into dependencies.
        if pipeline_settings.get('_DJBLETS_LESS_ALWAYS_REBUILD', False):
            return True

        outfile_mtime = self._get_mtime(outfile)

        if self._is_file_timestamp_outdated(infile, outfile_mtime):
            return True

        try:
            # If the file is in the cache, then start by trusting that the
            # imports haven't changed. We know this file is up-to-date (since
            # we checked above). We'll next be checking each dependency
            # (potentially invalidating all or part of the file cache, if we
            # find one that is out-of-date).
            files = self._import_files_cache[infile]
        except KeyError:
            # Parse out a deep list of the imported files and check those.
            files = self._get_import_files(infile)

            if files is None:
                # We've already logged. Consider this file outdated.
                return True

            self._import_files_cache[infile] = files

        outdated_deps = [
            dep
            for dep in files
            if self._is_file_timestamp_outdated(dep, outfile_mtime)
        ]

        if outdated_deps:
            # Any of the dependencies we found will have already invalidated
            # any file import caches referencing them. Just log and return.
            logging.info('Recompiling %s because one or more dependencies '
                         '(%s) are out of date.',
                         infile, ', '.join(outdated_deps))

            return True

        return False

    def _is_file_timestamp_outdated(self, filename, compare_mtime):
        """Return whether a file's timestamp is outdated.

        If the file is outdated, any cached entries referencing the file will
        be cleared out so that they can be refetched on the next compilation
        check.

        Args:
            filename (unicode):
                The filename to look up.

            compare_mtime (int):
                A pre-fetched mtime to compare the file's mtime to.

        Returns:
            bool:
            ``True`` if the file is outdated. ``False`` if it is up-to-date.
        """
        if compare_mtime is None:
            outdated = True
        else:
            mtime = self._get_mtime(filename)
            outdated = (mtime is None or mtime > compare_mtime)

        if outdated:
            # Since this can run concurrently with other operations, we need
            # to take care not to assume the presence of any keys.
            import_files_cache = self._import_files_cache
            import_files_cache.pop(filename, None)

            for key, files in list(six.iteritems(import_files_cache)):
                if filename in files:
                    import_files_cache.pop(key, None)

        return outdated

    def _get_import_files(self, filename):
        """Return the files imported when compiling a LessCSS file.

        This will return all files that are ultimately imported by a file,
        recursively. That means it will include files imported by files
        imported by ``filename``.

        Args:
            filename (unicode):
                The filename to return imports for.

        Returns:
            set of unicode:
            The filenames imported, or ``None`` if there was an error
            parsing any of the files.
        """
        p = subprocess.Popen(self.less_imports_command + [filename],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output, errors = p.communicate()

        rc = p.wait()

        if rc == 0:
            files = set(output.decode('utf-8').splitlines())
        else:
            logging.error('Error reading LessCSS imports from %s: %s',
                          filename, errors.decode('utf-8'))
            files = None

        return files

    def _get_mtime(self, filename):
        """Return the mtime for a file.

        This will utilize a cache that remains valid for only a short period
        of time, cutting back on redundant stat operations on the filesystem
        during the compilation phases.

        Args:
            filename (unicode):
                The filename to look up.

        Returns:
            int:
            The file's mtime, or ``None`` if the file was not found.
        """
        cls = type(self)
        cache = cls._mtime_cache
        stamp = cls._mtime_cache_stamp
        now = datetime.now()

        if not stamp or (now - stamp).seconds > self._MTIME_CACHE_STALE_SECS:
            cache.clear()
            cls._mtime_cache_stamp = now

        try:
            mtime = cache[filename]
        except KeyError:
            try:
                mtime = os.path.getmtime(filename)
            except OSError:
                mtime = None

            cache[filename] = mtime

        return mtime
