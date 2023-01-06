"""Mixins for writing Pipeline compilers.

Version Added:
    4.0
"""

import json
import logging
import os
from typing import List

from djblets.cache.backend import cache_memoize


logger = logging.getLogger(__name__)


class SourceMapStaleCheckMixin:
    """Pipeline compiler mixin for using sourcemaps for stale file checks.

    This mixin allows Pipeline compilers to use generated sourcemaps to
    determine which files were used to generate a compiled file, and to check
    each of those to see if the compile file is stale.

    This requires that the tool performing either CSS or JavaScript compilation
    is capable of generating a sourcemap that includes a comprehensive set of
    all files used in its compilation. Some tools (such as LessCSS) generate
    sourcemaps that only contain a subset, and those cannot be used without
    additional post-processing.

    The list of sources from parsing a sourcemap are cached for an hour, and
    will be invalidated any time the timestamp of the sourcemap or compiled
    file changes.

    Version Added:
        4.0
    """

    #: Cache expiration time for sourcemap sources.
    #:
    #: Version Added:
    #:     4.0
    _SOURCES_CACHE_TIME_SECS: int = 60 * 60

    def get_sourcemap_filename(
        self,
        infile: str,
        outfile: str,
    ) -> str:
        """Return the filename for the sourcemap.

        This defaults to adding ``.map`` to the end of the compiled file path.
        Subclasses can change this if they need to look for a file in a
        different location or with a different name.

        Args:
            infile (str):
                The source file path.

            outfile (str):
                The compiled file path.

        Returns:
            str:
            The sourcemap file path.
        """
        return '%s.map' % outfile

    def is_outdated(
        self,
        infile: str,
        outfile: str,
    ) -> bool:
        """Return whether a compiled file is out of date.

        This will check the timestamps of the source file, compiled file,
        sourcemap, and all files referenced by the sourcemap. If the
        source file or any of the sourcemap's source files have changed (or
        are missing), this will trigger recompilation.

        If a sourcemap is missing, this will log an error and will flag the
        file as being out of date.

        Args:
            infile (str):
                The source file path.

            outfile (str):
                The compiled file path.

        Returns:
            bool:
            ``True`` if the compiled file is out of date. ``False`` if it is
            not.
        """
        sourcemap_filename = self.get_sourcemap_filename(infile, outfile)

        if not os.path.exists(sourcemap_filename):
            if os.path.exists(outfile):
                logging.warning(
                    'Could not find source map "%s" for "%s". Please make '
                    'sure you have configured your Pipeline compiler '
                    'settings to emit a source map for this type of file.',
                    sourcemap_filename, outfile)

            return True

        try:
            infile_mtime = os.path.getmtime(infile)
            outfile_mtime = os.path.getmtime(outfile)
            sourcemap_mtime = os.path.getmtime(sourcemap_filename)
        except (FileNotFoundError, OSError):
            return True

        # There may be a discrepancy between the outfile and sourcemap
        # modification times. We'll trust that nothing was hand-modified,
        # and instead just choose the oldest of the two.
        checked_mtime = min(outfile_mtime, sourcemap_mtime)

        if infile_mtime > checked_mtime:
            return True

        # We'll cache the parsing of sources from the sourcemap, keyed off by
        # the file path and the modification time. This way we don't have to
        # load a potentially large file every time we want to check this.
        classname = type(self).__name__
        sourcemap_sources_key = (
            f'{classname}-sourcemap-sources:{sourcemap_filename}:'
            f'{sourcemap_mtime}'
        )

        try:
            sources = cache_memoize(
                sourcemap_sources_key,
                lambda: self._get_sourcemap_sources(sourcemap_filename))
        except IOError as e:
            logger.exception('Error opening source map file "%s": %s',
                             sourcemap_filename, e)
            return True
        except Exception as e:
            logger.exception('Error parsing source map file "%s": %s',
                             sourcemap_filename, e)
            return True

        # Check each source file to determine if the compiled file is stale.
        base_path = os.path.dirname(outfile)

        try:
            for filename in sources:
                filename = os.path.normpath(os.path.join(base_path, filename))

                if os.path.getmtime(filename) > checked_mtime:
                    return True
        except (FileNotFoundError, OSError):
            return True

        return False

    def _get_sourcemap_sources(
        self,
        sourcemap_path: str,
    ) -> List[str]:
        """Return sources from a sourcemap.

        This will open the sourcemap, deserialize it, and return the list of
        sources.

        Results from this are cached.

        Args:
            sourcemap_path (str):
                The path to the sourcemap.

        Returns:
            list of str:
            The sources listed in the sourcemap.
        """
        # Let exceptions bubble up, so we don't cache error results.
        with open(sourcemap_path, 'r') as fp:
            sourcemap = json.load(fp)

        return sourcemap.get('sources', [])
