"""Miscellaneous utilities."""

import logging
import os
import signal
import sys
from contextlib import contextmanager

from django.utils.translation import gettext as _


logger = logging.getLogger(__name__)


def kill_process(pid):
    """Kill a process."""
    # This is necessary because we need to continue supporting Python 2.5,
    # which doesn't have Popen.kill(). This is inspired by
    # http://stackoverflow.com/questions/1064335
    if sys.platform == 'win32':
        import ctypes
        PROCESS_TERMINATE = 1
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_TERMINATE, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGKILL)


@contextmanager
def controlled_subprocess(process_name, process):
    """
    A context manager for a subprocess that guarantees that a process
    is terminated, even if exceptions are thrown while using it.

    The process_name argument is used for logging when the process goes
    down fighting.  The process argument is a process returned by
    subprocess.Popen.

    Example usage:

    process = subprocess.Popen(['patch', '-o', newfile, oldfile])

    with controlled_subprocess("patch", process) as p:
        # ... do things with the process p

    Once outside the with block, you can rest assured that the subprocess
    is no longer running.
    """

    caught_exception = None

    try:
        yield process
    except Exception as e:
        caught_exception = e

    # If we haven't gotten a returncode at this point, we assume the
    # process is blocked.  Let's kill it.
    if process.returncode is None and process.poll() is None:
        logger.warning(
            'The process "%(name)s" with PID "%(pid)s" did not exit '
            'cleanly and will be killed automatically.'
            % {
                'name': process_name,
                'pid': process.pid,
            })

        kill_process(process.pid)

        # Now that we've killed the process, we'll grab the return code,
        # in order to clear the zombie.
        process.wait()

    # If we caught an exception earlier, re-raise it.
    if caught_exception:
        raise caught_exception
