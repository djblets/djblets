#
# handlers.py -- Custom logging handlers
#
# Copyright (c) 2010  Christian Hammond
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
#

import logging
import os
from stat import ST_DEV, ST_INO


# This is a port of Python 2.6's WatchedFileHandler. It should only be
# used if logging.handlers.WatchedFileHandler can't be imported.
#
# This class is copyright by the Python Software Foundation.
# See http://www.python.org/psf/license/ for details.
class WatchedFileHandler(logging.FileHandler):
    """
    A handler for logging to a file, which watches the file
    to see if it has changed while in use. This can happen because of
    usage of programs such as newsyslog and logrotate which perform
    log file rotation. This handler, intended for use under Unix,
    watches the file to see if it has changed since the last emit.
    (A file has changed if its device or inode have changed.)
    If it has changed, the old file stream is closed, and the file
    opened to get a new stream.

    This handler is not appropriate for use under Windows, because
    under Windows open files cannot be moved or renamed - logging
    opens the files with exclusive locks - and so there is no need
    for such a handler. Furthermore, ST_INO is not supported under
    Windows; stat always returns zero for this value.

    This handler is based on a suggestion and patch by Chad J.
    Schroeder.
    """
    def __init__(self, filename, mode='a', encoding=None, delay=0):
        logging.FileHandler.__init__(self, filename, mode, encoding)

        if not os.path.exists(self.baseFilename):
            self.dev, self.ino = -1, -1
        else:
            stat = os.stat(self.baseFilename)
            self.dev, self.ino = stat[ST_DEV], stat[ST_INO]

    def emit(self, record):
        """
        Emit a record.

        First check if the underlying file has changed, and if it
        has, close the old stream and reopen the file to get the
        current stream.
        """
        if not os.path.exists(self.baseFilename):
            stat = None
            changed = 1
        else:
            stat = os.stat(self.baseFilename)
            changed = (stat[ST_DEV] != self.dev) or (stat[ST_INO] != self.ino)
        if changed and self.stream is not None:
            self.stream.flush()
            self.stream.close()
            self.stream = self._open()
            if stat is None:
                stat = os.stat(self.baseFilename)
            self.dev, self.ino = stat[ST_DEV], stat[ST_INO]
        logging.FileHandler.emit(self, record)
