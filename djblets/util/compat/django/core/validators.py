"""Compatibility fallbacks for django.core.validators."""

# TODO: Remove this once we no longer support Django prior to 1.8.
#
# Copyright (c) Django Software Foundation and individual contributors.  All
# rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be
#     used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re

from django.core.exceptions import ValidationError
from django.core.validators import (RegexValidator, URLValidator,
                                    validate_ipv6_address)
from django.utils.translation import gettext_lazy as _
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit


# Prior to Django 1.8, URLValidator couldn't parse URLs that included inline
# credentials. This is a backport of the one that can.

if not hasattr(URLValidator, 'hostname_re'):
    class URLValidator(RegexValidator):
        ul = '\u00a1-\uffff'  # unicode letters range (must not be a raw string)

        # IP patterns
        ipv4_re = r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}'
        ipv6_re = r'\[[0-9a-f:\.]+\]'  # (simple regex, validated later)

        # Host patterns
        hostname_re = r'[a-z' + ul + r'0-9](?:[a-z' + ul + r'0-9-]{0,61}[a-z' + ul + r'0-9])?'
        # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
        domain_re = r'(?:\.(?!-)[a-z' + ul + r'0-9-]{1,63}(?<!-))*'
        tld_re = (
            r'\.'                                # dot
            r'(?!-)'                             # can't start with a dash
            r'(?:[a-z' + ul + '-]{2,63}'         # domain label
            r'|xn--[a-z0-9]{1,59})'              # or punycode label
            r'(?<!-)'                            # can't end with a dash
            r'\.?'                               # may have a trailing dot
        )
        host_re = '(' + hostname_re + domain_re + tld_re + '|localhost)'

        regex = re.compile(
            r'^(?:[a-z0-9\.\-\+]*)://'  # scheme is validated separately
            r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
            r'(?:' + ipv4_re + '|' + ipv6_re + '|' + host_re + ')'
            r'(?::\d{2,5})?'  # port
            r'(?:[/?#][^\s]*)?'  # resource path
            r'\Z', re.IGNORECASE)
        message = _('Enter a valid URL.')
        schemes = ['http', 'https', 'ftp', 'ftps']

        def __init__(self, schemes=None, **kwargs):
            super(URLValidator, self).__init__(**kwargs)
            if schemes is not None:
                self.schemes = schemes

        def __call__(self, value):
            # Check first if the scheme is valid
            scheme = value.split('://')[0].lower()
            if scheme not in self.schemes:
                raise ValidationError(self.message, code=self.code)

            # Then check full URL
            try:
                super(URLValidator, self).__call__(value)
            except ValidationError as e:
                # Trivial case failed. Try for possible IDN domain
                if value:
                    try:
                        scheme, netloc, path, query, fragment = urlsplit(value)
                    except ValueError:  # for example, "Invalid IPv6 URL"
                        raise ValidationError(self.message, code=self.code)
                    try:
                        netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
                    except UnicodeError:  # invalid domain part
                        raise e
                    url = urlunsplit((scheme, netloc, path, query, fragment))
                    super(URLValidator, self).__call__(url)
                else:
                    raise
            else:
                # Now verify IPv6 in the netloc part
                host_match = re.search(r'^\[(.+)\](?::\d{2,5})?$', urlsplit(value).netloc)
                if host_match:
                    potential_ip = host_match.groups()[0]
                    try:
                        validate_ipv6_address(potential_ip)
                    except ValidationError:
                        raise ValidationError(self.message, code=self.code)

            # The maximum length of a full host name is 253 characters per RFC 1034
            # section 3.1. It's defined to be 255 bytes or less, but this includes
            # one byte for the length of the name and one byte for the trailing dot
            # that's used to indicate absolute names in DNS.
            if len(urlsplit(value).netloc) > 253:
                raise ValidationError(self.message, code=self.code)


__all__ = [
    'URLValidator',
]
