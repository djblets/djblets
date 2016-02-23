"""A specialization of pipeline's ES6Compiler."""

from __future__ import unicode_literals

from pipeline.compilers.es6 import ES6Compiler as PipelineES6Compiler


class ES6Compiler(PipelineES6Compiler):
    """An ES6 Compiler which compiles .es6.js to .js.

    To use this, add the path to this class to
    ``settings.PIPELINE['COMPILERS']``.
    """

    input_extension = 'es6.js'

    def match_file(self, path):
        """Return whether the given path should use this compiler.

        Args:
            path (unicode):
                The source path.

        Returns:
            bool:
            Whether this compiler should be used for the given path.
        """
        return path.endswith(self.input_extension)

    def output_path(self, path, extension):
        """Return the path of the output file for this compiler.

        Args:
            path (unicode):
                The input path.

            extension (unicode):
                The target file extension.

        Returns:
            unicode:
            The input path with .es6.js renamed to .js.
        """
        assert path.endswith(self.input_extension)
        return path[:-len(self.input_extension)] + extension
