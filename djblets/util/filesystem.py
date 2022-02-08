"""Filesystem-related utilities."""

import os
import sys


def is_exe_in_path(name):
    """Checks whether an executable is in the user's search path.

    This expects a name without any system-specific executable extension.
    It will append the proper extension as necessary. For example,
    use "myapp" and not "myapp.exe".

    This will return True if the app is in the path, or False otherwise.
    """

    if sys.platform == 'win32' and not name.endswith('.exe'):
        name += ".exe"

    for dir in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(dir, name)):
            return True

    return False
