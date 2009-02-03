#
# djblets/util/context_processors.py
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
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

import os
from datetime import datetime

from django.conf import settings

def settingsVars(request):
    return {'settings': settings}

def siteRoot(request):
    """
    Exposes a SITE_ROOT variable in templates. This assumes that the
    project has been configured with a SITE_ROOT settings variable and
    proper support for basing the installation in a subdirectory.
    """
    return {'SITE_ROOT': settings.SITE_ROOT}


MEDIA_SERIAL = 0

def mediaSerial(request):
    """
    Exposes a media serial number that can be appended to a media filename
    in order to make a URL that can be cached forever without fear of change.
    The next time the file is updated and the server is restarted, a new
    path will be accessed and cached.

    If settings.MEDIA_SERIAL exists, this will use that. Otherwise, it will
    crawl the media files (using directories in MEDIA_SERIAL_DIRS if
    specified, or all of MEDIA_ROOT otherwise), figuring out the latest
    timestamp, and use that instead.
    """
    global MEDIA_SERIAL

    if hasattr(settings, "MEDIA_SERIAL"):
        MEDIA_SERIAL = settings.MEDIA_SERIAL
    elif MEDIA_SERIAL == 0:
        media_dirs = getattr(settings, "MEDIA_SERIAL_DIRS", ["."])

        for media_dir in media_dirs:
            media_path = os.path.join(settings.MEDIA_ROOT, media_dir)

            for root, dirs, files in os.walk(media_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > MEDIA_SERIAL:
                        MEDIA_SERIAL = mtime

        setattr(settings, "MEDIA_SERIAL", MEDIA_SERIAL)

    return {'MEDIA_SERIAL': MEDIA_SERIAL}


AJAX_SERIAL = 0

def ajaxSerial(request):
    """
    Exposes a serial number that can be appended to filenames involving
    dynamic loads of URLs in order to make a URL that can be cached forever
    without fear of change.

    If settings.AJAX_SERIAL exists, this will use that. Otherwise, it will
    crawl the template files (using directories in TEMPLATE_DIRS), figuring
    out the latest timestamp, and use that instead.
    """
    global AJAX_SERIAL

    if hasattr(settings, "AJAX_SERIAL"):
        AJAX_SERIAL = settings.AJAX_SERIAL
    elif AJAX_SERIAL == 0:
        template_dirs = getattr(settings, "TEMPLATE_DIRS", ["."])

        for template_path in template_dirs:
            for root, dirs, files in os.walk(template_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > AJAX_SERIAL:
                        AJAX_SERIAL = mtime

        setattr(settings, "AJAX_SERIAL", AJAX_SERIAL)

    return {'AJAX_SERIAL': AJAX_SERIAL}
