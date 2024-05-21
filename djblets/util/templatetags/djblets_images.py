"""Image-related template tags."""

from __future__ import annotations

import io
import logging
import os
import re
from typing import Optional, TYPE_CHECKING, Union

from django import template
from django.core.files.base import File
from django.template import TemplateSyntaxError
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _
from PIL import Image
from PIL.Image import registered_extensions

from djblets.util.decorators import blocktag

if TYPE_CHECKING:
    from django.core.files.storage import Storage


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
def thumbnail(
    f: Union[File, str],
    size: Union[str, tuple[Optional[int], Optional[int]]] = '400x100',
    *,
    create_if_missing: bool = True,
    storage: Optional[Storage] = None,
) -> Optional[str]:
    """Create a thumbnail of the given image.

    This will create a thumbnail of the given file, which may be a file
    path within storage, a :py:class:`~django.core.files.base.File` instance
    representing a file in storage, or a file instance retrieved from a
    :py:class:~django.db.models.FileField`.

    The thumbnail will be of the given size. This size can either be specified
    as a string of WIDTHxHEIGHT (in pixels), or a 2-tuple. If the size is a
    tuple and one of the values is None, that value will be set automatically
    to preserve the aspect ratio.

    If the file format is not supported, then the file path will be returned
    as-is.

    Version Changed:
        5.0:
        * Added ``create_if_missing`` and ``storage`` options.
        * Added support for working with general
          :py:class:`~django.core.files.base.File` objects or file paths
          within storage, when providing the ``storage`` parameter.

    Args:
        f (django.db.models.fields.files.FieldFile):
            The file path within storage,
            :py:class:`~django.core.files.base.File` instance, or a
            :py:class:`~django.db.models.FileField`-backed file.

            if not providing a field-backed file, then ``storage`` must be
            provided.

            Version Changed:
                5.0:
                This may now be a file path within storage or a
                :py:class:`~django.core.files.base.File` instance.

        size (str or tuple of int):
            The thumbnail constraint size.

            This can either be a string in ``WIDTHxHEIGHT`` form, or a
            tuple in ``(width, height)`` form. In the latter, the height
            is optional.

        create_if_missing (bool, optional):
            Whether to create the thumbnail if one does not already exist.

            If ``False``, the existing thumbnail URL will be returned if it
            exists, but a new one will not otherwise be created.

            Version Added:
                5.0

        storage (django.core.files.storage.Storage, optional):
            The storage backend for the file.

            This is required if the file does not provide its own ``storage``
            attribute, and is ignored if it does.

            Version Added:
                5.0

    Returns:
        str:
        The URL to the thumbnail.

        This will be ``None`` if the thumbnail does not exist and passing
        ``create_if_missing=False``.

    Raises:
        ValueError:
            The thumbnail size was not in a valid format.
    """
    filename: Optional[str]
    x: Optional[int]
    y: Optional[int]

    if isinstance(f, str):
        filename = f
    elif isinstance(f, File):
        filename = f.name

        if not filename:
            raise ValueError(_(
                'The provided file does not have a filename set.'
            ))
    else:
        raise ValueError(_(
            'The provided file to thumbnail is not a supported value.'
        ))

    storage = getattr(f, 'storage', storage)

    if storage is None:
        raise ValueError(_(
            'A file storage backend could not be found for the provided '
            'file.'
        ))

    basename, ext = os.path.splitext(filename)

    # Make sure that this is a supported image file type.
    if ext.lower() not in registered_extensions():
        return storage.url(filename)

    # Convert the size requirement to dimensions.
    try:
        if isinstance(size, str):
            # This will raise a ValueError if the string contains either
            # too many values or non-integer values.
            x, y = (int(x) for x in size.split('x'))
            size_str = size
        elif isinstance(size, tuple):
            x, y = size

            if x is None and y is None:
                raise ValueError
            elif y is None:
                size_str = f'{x}'
            elif x is None:
                size_str = f'x{y}'
            else:
                size_str = f'{x}x{y}'
        else:
            raise ValueError
    except ValueError:
        raise ValueError(f'Thumbnail size {size!r} is not valid.')

    miniature = f'{basename}_{size_str}{ext}'

    if not storage.exists(miniature):
        if not create_if_missing:
            return None

        try:
            with storage.open(filename, 'rb') as fp:
                image = Image.open(io.BytesIO(fp.read()))

            if y is None:
                assert x is not None
                x = min(image.size[0], x)

                # Calculate height based on width.
                y = int(x * (image.size[1] / image.size[0]))
            elif x is None:
                assert y is not None
                y = min(image.size[1], y)

                # Calculate height based on height.
                x = int(y * (image.size[0] / image.size[1]))

            # Pillow is aggressively deprecating Image.ANTIALIAS. Conditionally
            # attempt to use the new name.
            if hasattr(Image, 'Resampling'):
                # 9.1.0+
                antialias = Image.Resampling.LANCZOS
            else:
                # 9.0.x and below
                antialias = Image.ANTIALIAS

            image.thumbnail((x, y), antialias)

            save_image_to_storage(image, storage, miniature)
        except (IOError, KeyError) as e:
            logger.exception('Error thumbnailing image file %s and saving '
                             'as %s: %s',
                             filename, miniature, e)
            return ''

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

    for descriptor, url in sources.items():
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
        raise TemplateSyntaxError(str(e))


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
