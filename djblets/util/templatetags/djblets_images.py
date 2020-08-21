#
# djblets_images.py -- Image-related template tags
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

from __future__ import division, unicode_literals

import io
import logging
import os
import re

from django import template
from django.template import TemplateSyntaxError
from django.utils import six
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext as _
from PIL import Image
from PIL.Image import registered_extensions

from djblets.util.decorators import blocktag


logger = logging.getLogger(__name__)
register = template.Library()


def save_image_to_storage(image, storage, filename):
    """Save an image to storage."""
    f = storage.open(filename, mode='w+b')
    image.save(f, 'png')
    f.close()


@register.simple_tag
def crop_image(f, x, y, width, height):
    """
    Crops an image at the specified coordinates and dimensions, returning the
    resulting URL of the cropped image.
    """
    filename = f.name
    storage = f.storage
    basename = filename

    if filename.find(".") != -1:
        basename = filename.rsplit('.', 1)[0]
    new_name = '%s_%d_%d_%d_%d.png' % (basename, x, y, width, height)

    if not storage.exists(new_name):
        try:
            f = storage.open(filename)
            data = io.BytesIO(f.read())
            f.close()

            image = Image.open(data)
            image = image.crop((x, y, x + width, y + height))

            save_image_to_storage(image, storage, new_name)
        except (IOError, KeyError) as e:
            logger.exception('Error cropping image file %s at %d, %d, %d, %d '
                             'and saving as %s: %s',
                             filename, x, y, width, height, new_name, e)
            return ""

    return storage.url(new_name)


@register.filter
def thumbnail(f, size='400x100'):
    """Create a thumbnail of the given image.

    This will create a thumbnail of the given ``file`` (a Django FileField or
    ImageField) with the given size. Size can either be a string of WxH (in
    pixels), or a 2-tuple. If the size is a tuple and the second part is None,
    it will be calculated to preserve the aspect ratio.

    If the image format is not registered in PIL the thumbnail is not generated
    and returned as-is.

    This will return the URL to the stored thumbnail.
    """
    storage = f.storage
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in registered_extensions():
        return storage.url(f.name)

    if isinstance(size, six.string_types):
        x, y = (int(x) for x in size.split('x'))
        size_str = size
    elif isinstance(size, tuple):
        x, y = size

        if y is None:
            size_str = '%d' % x
        else:
            size_str = '%dx%d' % (x, y)
    else:
        raise ValueError('Thumbnail size "%r" could not be be parsed', size)

    filename = f.name
    if filename.find(".") != -1:
        basename, format = filename.rsplit('.', 1)
        miniature = '%s_%s.%s' % (basename, size_str, format)
    else:
        basename = filename
        miniature = '%s_%s' % (basename, size_str)

    if not storage.exists(miniature):
        try:
            f = storage.open(filename, 'rb')
            data = io.BytesIO(f.read())
            f.close()

            image = Image.open(data)

            if y is None:
                x = min(image.size[0], x)

                # Calculate height based on width
                y = int(x * (image.size[1] / image.size[0]))

            image.thumbnail([x, y], Image.ANTIALIAS)

            save_image_to_storage(image, storage, miniature)
        except (IOError, KeyError) as e:
            logger.exception('Error thumbnailing image file %s and saving '
                             'as %s: %s',
                             filename, miniature, e)
            return ""

    return storage.url(miniature)


def build_srcset(sources):
    """Return the source set attribute value for the given sources.

    The resulting sources will be sorted by value, with the pixel density
    (``x``) values coming before width (``w``) values.

    Args:
        sources (dict):
            A mapping of descriptors (e.g., ``'2x'`` or ``'512w'``) that
            describe the requirement for the source to be shown to URLs.

    Returns:
        unicode:
        The returned ``srcset`` attribute value.
    """
    sources_info = []

    for descriptor, url in six.iteritems(sources):
        if not url:
            continue

        if not descriptor:
            descriptor = '1x'

        valid = descriptor.endswith(('x', 'w'))

        if valid:
            try:
                sources_info.append((descriptor, float(descriptor[:-1]), url))
            except ValueError:
                valid = False

        if not valid:
            raise ValueError(_('"%s" is not a valid srcset size descriptor.')
                             % descriptor)

    # Sort the sources such that 'x' descriptors are always before 'w'
    # descriptors, and in numerical order.
    descriptor_sort_values = {
        'x': -1,
        'w': 1,
    }

    sources_info = sorted(
        sources_info,
        key=lambda source: (descriptor_sort_values[source[0][-1]], source[1]))

    return format_html_join(
        ', ',
        '{0} {1}',
        (
            (url, descriptor)
            for descriptor, descriptor_value, url in sources_info
        ))


@register.simple_tag
def srcset(sources):
    """Render the source set attribute value for the given sources.

    The resulting sources will be sorted by value, with the pixel density
    (``x``) values coming before width (``w``) values.

    Args:
        sources (dict):
            A mapping of descriptors (e.g., ``'2x'`` or ``'512w'``) that
            describe the requirement for the source to be shown to URLs.

    Returns:
        unicode:
        The rendered ``srcset`` attribute value.
    """
    try:
        return build_srcset(sources)
    except ValueError as e:
        raise TemplateSyntaxError(six.text_type(e))


@register.tag
@blocktag(end_prefix='end_')
def image_source_attrs(context, nodelist, *options):
    """Render source attributes for an image tag.

    This will render ``src="..." srcset="..."`` attributes for an ``<img>``
    tag, based on the sources provided in the tag's content. There should be
    one source definition per line (with an optional trailing comma) in the
    form of::

        <descriptor> <URL>

    These will get turned into a ``srcset``, and the ``1x`` descriptor (which
    is required) will be set as the ``src`` attribute.

    Args:
        block_content (unicode):
            The block content containing image sources.

    Returns:
        Attributes for the ``<img>`` tag.

    Example:
        .. code-block:: html+django

           <img {% image_source_attrs %}
                1x {%  static "images/myimage.png" %}
                2x {%  static "images/myimage@2x.png" %}
                3x {%  static "images/myimage@3x.png" %}
                {% end_image_source_attrs %}>
    """
    content = nodelist.render(context).strip()

    try:
        sources = {}

        for source in re.split(r',|\n+', content):
            source = source.strip()

            if source:
                descriptor, url = source.split(' ', 1)
                sources[descriptor.strip()] = url.strip()

    except ValueError:
        raise TemplateSyntaxError(_(
            'The source definition passed to {% image_source_attrs %} is '
            'not structured correctly. Make sure that there is one source '
            'definition per line and that it contains a descriptor and a '
            'URL.'))

    try:
        src_value = sources['1x']
    except KeyError:
        raise TemplateSyntaxError(_(
            'The source definition passed to {% image_source_attr %} must '
            'contain a "1x" descriptor.'))

    return format_html('src="{0}" srcset="{1}"', src_value,
                       build_srcset(sources))
