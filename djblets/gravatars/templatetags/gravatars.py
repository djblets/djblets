#
# gravatars.py -- Decorational template tags
#
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

from md5 import md5

from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag
def gravatar(user, size=None):
    """
    Outputs the HTML for displaying a user's gravatar.

    This can take an optional size of the image (defaults to 80 if not
    specified).

    This is also influenced by the following settings:

        GRAVATAR_SIZE    - Default size for gravatars
        GRAVATAR_RATING  - Maximum allowed rating (g, pg, r, x)
        GRAVATAR_DEFAULT - Default image set to show if the user hasn't
                           specified a gravatar (identicon, monsterid, wavatar)

    See http://www.gravatar.com/ for more information.
    """
    if not user.email:
        return ""

    email = user.email.strip().lower()
    email_hash = md5(email).hexdigest()

    url = "http://www.gravatar.com/avatar/%s.jpg" % email_hash
    params = []

    if not size and hasattr(settings, "GRAVATAR_SIZE"):
        size = settings.GRAVATAR_SIZE

    if size:
        params.append("s=%s" % size)

    if hasattr(settings, "GRAVATAR_RATING"):
        params.append("r=%s" % settings.GRAVATAR_RATING)

    if hasattr(settings, "GRAVATAR_DEFAULT"):
        params.append("d=%s" % settings.GRAVATAR_DEFAULT)

    if params:
        url += "?" + "&".join(params)

    return '<img src="%s" width="%s" height="%s" alt="%s"/>' % \
           (url, size, size, user.get_full_name() or user.username)
