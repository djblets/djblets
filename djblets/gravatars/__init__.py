#
# __init__.py -- Gravatar functionality
#
# Copyright (c) 2012       Beanbag, Inc.
# Copyright (c) 2008-2009  Christian Hammond
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

from __future__ import unicode_literals

from hashlib import md5
from warnings import warn

from django.conf import settings
from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode


default_app_config = 'djblets.gravatars.apps.GravatarsAppConfig'


def get_gravatar_url_for_email(email=None, size=None):
    """Return the Gravatar URL for an e-mail address.

    The returned URL will always use HTTPS.

    Note that callers adhering to the GDPR should check for a user's consent
    before displaying a Gravatar on their behalf. This is checked automatically
    if using :py:mod:`djblets.avatars`.

    Args:
        email (unicode):
            The e-mail address to get the Gravatar URL for.

        size (int, optional):
            An optional height and width of the image (in pixels).

    Returns:
        unicode:
        The URL for the Gravatar associated with the given e-mail address.
    """
    if email:
        email = email.strip().lower()

        if isinstance(email, six.text_type):
            email = email.encode('utf-8')

        email_hash = md5(email).hexdigest()
    else:
        email_hash = '00000000000000000000000000000000'

    url = 'https://secure.gravatar.com/avatar/%s' % email_hash
    params = []

    if not size and hasattr(settings, 'GRAVATAR_SIZE'):
        size = settings.GRAVATAR_SIZE

    if size:
        params.append(('s', size))

    if hasattr(settings, 'GRAVATAR_RATING'):
        params.append(('r', settings.GRAVATAR_RATING))

    if hasattr(settings, 'GRAVATAR_DEFAULT'):
        params.append(('d', settings.GRAVATAR_DEFAULT))

    if params:
        url = '%s?%s' % (url, urlencode(params))

    return url


def get_gravatar_url(user=None, size=None):
    """Return the Gravatar URL for a user.

    The returned URL will always use HTTPS.

    Note that callers adhering to the GDPR should check for a user's consent
    before displaying a Gravatar on their behalf. This is checked automatically
    if using :py:mod:`djblets.avatars`.

    Args:
        user (django.contrib.auth.models.User):
            The user whose Gravatar URL is to be retrieved.

        size (int, optional):
            An optional height and width of the image (in pixels).

    Returns:
        unicode:
        The URL for the user's Gravatar.

    Raises:
        ValueError:
            Raised if ``user`` is ``None``.
    """
    if user is None:
        raise ValueError('"user" cannot be None.')

    if user.is_anonymous() or not user.email:
        return ''

    return get_gravatar_url_for_email(email=user.email, size=size)
