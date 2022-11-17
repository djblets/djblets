"""A pipeline compiler for TypeScript.

Version Added:
    4.0
"""

from pipeline.compilers.es6 import ES6Compiler


class TypeScriptCompiler(ES6Compiler):
    """A pipeline compiler which compiles .ts to .js.

    To use this, add the path to this class to
    ``settings.PIPELINE['COMPILERS']``.

    Version Added:
        4.0
    """

    input_extension = 'ts'

    def match_file(
        self,
        path: str,
    ) -> bool:
        """Return whether the given path should use this compiler.

        Args:
            path (str):
                The source path.

        Returns:
            bool:
            Whether this compiler should be used for the given path.
        """
        return path.endswith(self.input_extension)
