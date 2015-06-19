# TODO: Remove this file once we no longer support a version of Django
#       prior to 1.7.
#
# This is Django 1.6.11's django/core/cache.py.
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

from django.core.cache.backends.base import InvalidCacheBackendError
from django.utils.six.moves.urllib.parse import parse_qsl


def parse_backend_uri(backend_uri):
    """
    Converts the "backend_uri" into a cache scheme ('db', 'memcached', etc), a
    host and any extra params that are required for the backend. Returns a
    (scheme, host, params) tuple.
    """
    if backend_uri.find(':') == -1:
        raise InvalidCacheBackendError("Backend URI must start with scheme://")
    scheme, rest = backend_uri.split(':', 1)
    if not rest.startswith('//'):
        raise InvalidCacheBackendError("Backend URI must start with scheme://")

    host = rest[2:]
    qpos = rest.find('?')

    if qpos != -1:
        params = dict(parse_qsl(rest[qpos + 1:]))
        host = rest[2:qpos]
    else:
        params = {}

    if host.endswith('/'):
        host = host[:-1]

    return scheme, host, params
