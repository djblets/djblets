import mimetools
import os
import re
import urllib2

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from compress.filter_base import FilterBase, FilterError
from django.conf import settings


LESSCSS_URL = getattr(settings, 'LESSCSS_URL',
                      'http://blesscss.cloudfoundry.com/min')
LESSCSS_IMPORT_PATHS = getattr(settings, 'LESSCSS_IMPORT_PATHS', [])


class LessCSSFilter(FilterBase):
    IMPORT_RE = re.compile(r'^@import "([^"]+)";')

    def filter_css(self, lesscss):
        if self.verbose:
            print 'Converting lesscss using %s' % LESSCSS_URL

        boundary = mimetools.choose_boundary()

        content  = '--%s\r\n' % boundary
        content += 'Content-Disposition: form-data; name="style.less"\r\n'
        content += '\r\n'

        for line in lesscss.splitlines(True):
            m = self.IMPORT_RE.match(line)

            if m:
                filename = m.group(1)

                if (not filename.endswith(".css") and
                    not filename.endswith(".less")):
                    filename += '.less'

                line = self._load_import(filename)

            content += line

        content += '\r\n'
        content += '--%s--\r\n' % boundary
        content += '\r\n'

        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
            'Content-Length': str(len(content)),
        }

        r = urllib2.Request(LESSCSS_URL, content, headers)

        try:
            return urllib2.urlopen(r).read()
        except urllib2.HTTPError, e:
            if e.code == 400:
                raise FilterError("Error processing lessCSS files: %s" %
                                  e.read())

            raise

    def _load_import(self, filename):
        for import_path in LESSCSS_IMPORT_PATHS:
            path = os.path.join(settings.MEDIA_ROOT, import_path, filename)

            if os.path.exists(path):
                fp = open(path, 'r')
                content = fp.read()
                fp.close()

                return content

        raise FilterError('Unable to find import file "%s"' % filename)
