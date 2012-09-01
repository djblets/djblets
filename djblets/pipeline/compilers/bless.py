import mimetools
import os
import re
import urllib2

from pipeline.compilers import CompilerBase, CompilerError
from django.conf import settings


BLESS_URL = getattr(settings, 'BLESS_URL',
                    'http://blesscss.cloudfoundry.com/min')
BLESS_IMPORT_PATHS = getattr(settings, 'BLESS_IMPORT_PATHS', [])


class BlessCompiler(CompilerBase):
    output_extension = 'css'
    IMPORT_RE = re.compile(r'^@import "([^"]+)";')

    def match_file(self, filename):
        return filename.endswith('.less')

    def compile_file(self, infile, outfile, *args, **kwargs):
        if self.verbose:
            print 'Converting lesscss using %s' % BLESS_URL

        boundary = mimetools.choose_boundary()

        blob  = '--%s\r\n' % boundary
        blob += 'Content-Disposition: form-data; name="style.less"\r\n'
        blob += '\r\n'

        try:
            fp = open(infile, 'r')
        except IOError, e:
            raise CompilerError('Unable to read file %s' % infile)

        content = fp.read()

        for line in content.splitlines(True):
            m = self.IMPORT_RE.match(line)

            if m:
                filename = m.group(1)

                if (not filename.endswith(".css") and
                    not filename.endswith(".less")):
                    filename += '.less'

                line = self._load_import(filename)

            blob += line

        fp.close()

        blob += '\r\n'
        blob += '--%s--\r\n' % boundary
        blob += '\r\n'

        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
            'Content-Length': str(len(blob)),
        }

        r = urllib2.Request(BLESS_URL, blob, headers)

        try:
            content = urllib2.urlopen(r).read()
        except urllib2.HTTPError, e:
            if e.code == 400:
                raise CompilerError("Error processing lessCSS files: %s" %
                                    e.read())

            raise

        fp = open(outfile, 'w')
        fp.write(content)
        fp.close()

        return content

    def _load_import(self, filename):
        for import_path in BLESS_IMPORT_PATHS:
            path = os.path.join(settings.STATIC_ROOT, import_path, filename)

            if os.path.exists(path):
                fp = open(path, 'r')
                content = fp.read()
                fp.close()

                return content

        raise CompilerError('Unable to find import file "%s"' % filename)
