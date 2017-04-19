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

import logging

from django import template
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO
from PIL import Image


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
            data = StringIO(f.read())
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

    This will return the URL to the stored thumbnail.
    """
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

    storage = f.storage

    if not storage.exists(miniature):
        try:
            f = storage.open(filename, 'rb')
            data = StringIO(f.read())
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
