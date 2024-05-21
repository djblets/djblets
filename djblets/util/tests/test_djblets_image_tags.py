"""Unit tests for djblets.util.templatetags.djblets_images."""

from __future__ import annotations

import io
import os
import shutil
import tempfile
from collections import OrderedDict

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template, TemplateSyntaxError

from PIL import Image
from djblets.testing.testcases import TestCase
from djblets.util.templatetags.djblets_images import thumbnail


class SrcSetTagTests(TestCase):
    """Unit tests for the {% srcset %} template tag."""

    def test_with_valid_sources(self):
        """Testing {% srcset %} with valid sources"""
        t = Template('{% load djblets_images %}'
                     '<img srcset="{% srcset sources %}">')

        self.assertEqual(
            t.render(Context({
                'sources': {
                    '1x': '/path/to/image.png',
                    '2x': '/path/to/image@2x.png',
                    '3x': '/path/to/image@3x.png',
                    '10w': '/path/to/image@10w.png',
                },
            })),
            '<img srcset="'
            '/path/to/image.png 1x, '
            '/path/to/image@2x.png 2x, '
            '/path/to/image@3x.png 3x, '
            '/path/to/image@10w.png 10w">')

    def test_with_invalid_sources(self):
        """Testing {% srcset %} with invalid sources"""
        t = Template('{% load djblets_images %}'
                     '<img srcset="{% srcset sources %}">')

        message = '"ax" is not a valid srcset size descriptor.'

        with self.assertRaisesMessage(TemplateSyntaxError, message):
            t.render(Context({
                'sources': {
                    'ax': '/path/to/image.png',
                },
            }))

    def test_sorts(self):
        """Testing {% srcset %} sorts sources"""
        t = Template('{% load djblets_images %}'
                     '<img srcset="{% srcset sources %}">')

        sources = OrderedDict()
        sources['100w'] = '/path/to/image@100w.png'
        sources['10w'] = '/path/to/image@10w.png'
        sources['3x'] = '/path/to/image@3x.png'
        sources['1x'] = '/path/to/image.png'
        sources['2x'] = '/path/to/image@2x.png'
        sources['20w'] = '/path/to/image@20w.png'
        sources['1.5x'] = '/path/to/image@1.5x.png'
        sources['2w'] = '/path/to/image@2w.png'
        sources['10x'] = '/path/to/image@10x.png'

        self.assertEqual(
            t.render(Context({
                'sources': sources,
            })),
            '<img srcset="'
            '/path/to/image.png 1x, '
            '/path/to/image@1.5x.png 1.5x, '
            '/path/to/image@2x.png 2x, '
            '/path/to/image@3x.png 3x, '
            '/path/to/image@10x.png 10x, '
            '/path/to/image@2w.png 2w, '
            '/path/to/image@10w.png 10w, '
            '/path/to/image@20w.png 20w, '
            '/path/to/image@100w.png 100w">')


class ImageSourceAttrsTagTests(TestCase):
    """Unit tests for the {% image_source_attrs %} template tag."""

    def test_with_valid_sources(self):
        """Testing {% image_source_attrs %} with valid sources"""
        t = Template(
            '{% load djblets_images %}'
            '<img {% image_source_attrs %}\n'
            '      1x /path/to/image.png\n'
            '      2x /path/to/image@2x.png\n'
            '      3x /path/to/image@3x.png\n'
            '      10w /path/to/image@10w.png\n'
            '     {% end_image_source_attrs %}>')

        self.assertEqual(
            t.render(Context()),
            '<img src="/path/to/image.png" srcset="'
            '/path/to/image.png 1x, '
            '/path/to/image@2x.png 2x, '
            '/path/to/image@3x.png 3x, '
            '/path/to/image@10w.png 10w">')

    def test_with_invalid_sources(self):
        """Testing {% image_source_attrs %} with invalid sources definition"""
        t = Template(
            '{% load djblets_images %}'
            '<img {% image_source_attrs %}\n'
            '      /path/to/image.png\n'
            '      2x /path/to/image@2x.png\n'
            '     {% end_image_source_attrs %}>')

        message = (
            'The source definition passed to {% image_source_attrs %} is '
            'not structured correctly. Make sure that there is one source '
            'definition per line and that it contains a descriptor and a '
            'URL.'
        )

        with self.assertRaisesMessage(TemplateSyntaxError, message):
            t.render(Context())

    def test_with_no_1x(self):
        """Testing {% image_source_attrs %} with no 1x source"""
        t = Template(
            '{% load djblets_images %}'
            '<img {% image_source_attrs %}\n'
            '      2x /path/to/image@2x.png\n'
            '      3x /path/to/image@3x.png\n'
            '     {% end_image_source_attrs %}>')

        message = (
            'The source definition passed to {% image_source_attr %} must '
            'contain a "1x" descriptor.'
        )

        with self.assertRaisesMessage(TemplateSyntaxError, message):
            t.render(Context())


class ThumbnailTests(TestCase):
    """Unit tests for the {% thumbnail %} template tag.

    Version Added:
        5.0
    """

    #: The root path for the test storage.
    _storage_root: str

    #: The storage instance.
    storage: FileSystemStorage

    def setUp(self) -> None:
        """Set up the test data for a single test run.

        This will create the storage root and instance for the thumbnail
        operations.
        """
        super().setUp()

        self._storage_root = tempfile.mkdtemp()
        self.storage = FileSystemStorage(location=self._storage_root)

    def tearDown(self) -> None:
        """Tear down test data after a single test run.

        This will erase the storage root and clear up the storage instance.
        """
        shutil.rmtree(self._storage_root)
        self.storage = None  # type: ignore

    def test_with_non_image(self) -> None:
        """Testing {% thumbnail %} with non-image file"""
        self.assertEqual(
            thumbnail(SimpleUploadedFile('test.txt', b'test'),
                      storage=self.storage),
            '/media/test.txt')

    def test_with_file_path(self) -> None:
        """Testing {% thumbnail %} with file path"""
        self._build_png_file('sample-wide.png')

        self.assertEqual(
            thumbnail('sample-wide.png',
                      storage=self.storage),
            '/media/sample-wide_400x100.png')

        self._check_image_size(name='sample-wide_400x100.png',
                               expected_width=150,
                               expected_height=100)

    def test_with_file_path_no_storage(self) -> None:
        """Testing {% thumbnail %} with file path and no storage"""
        message = (
            'A file storage backend could not be found for the provided '
            'file.'
        )

        with self.assertRaisesMessage(ValueError, message):
            thumbnail('sample-wide.png')

    def test_with_file_path_outside_storage(self) -> None:
        """Testing {% thumbnail %} with file path outside storage"""
        with self.assertRaises(SuspiciousFileOperation):
            thumbnail('/sample-wide.png',
                      storage=self.storage)

    def test_with_file_from_field(self) -> None:
        """Testing {% thumbnail %} with file from FileField"""
        # This is close enough. We just care about the storage attribute.
        file = self._build_png_file('sample-wide.png')
        setattr(file, 'storage', self.storage)

        self.assertEqual(
            thumbnail(file),
            '/media/sample-wide_400x100.png')

        self._check_image_size(name='sample-wide_400x100.png',
                               expected_width=150,
                               expected_height=100)

    def test_with_file_no_filename(self) -> None:
        """Testing {% thumbnail %} with File without a filename"""
        message = 'The provided file does not have a filename set.'

        with self.assertRaisesMessage(ValueError, message):
            thumbnail(File(name=None,
                           file=None))

    def test_with_image_defaults(self) -> None:
        """Testing {% thumbnail %} with image file and defaults"""
        self.assertEqual(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage),
            '/media/sample-wide_400x100.png')

        self._check_image_size(name='sample-wide_400x100.png',
                               expected_width=150,
                               expected_height=100)

    def test_with_size_string(self) -> None:
        """Testing {% thumbnail %} with size as string"""
        self.assertEqual(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size='150x180'),
            '/media/sample-wide_150x180.png')

        self._check_image_size(name='sample-wide_150x180.png',
                               expected_width=150,
                               expected_height=100)

    def test_with_size_string_invalid(self) -> None:
        """Testing {% thumbnail %} with size as invalid string"""
        message = "Thumbnail size '150x180xA' is not valid."

        with self.assertRaisesMessage(ValueError, message):
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size='150x180xA')

    def test_with_size_tuple(self) -> None:
        """Testing {% thumbnail %} with size as tuple"""
        self.assertEqual(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=(300, 250)),
            '/media/sample-wide_300x250.png')

        self._check_image_size(name='sample-wide_300x250.png',
                               expected_width=300,
                               expected_height=200)

    def test_with_size_tuple_width_only(self) -> None:
        """Testing {% thumbnail %} with size as tuple and width only"""
        self.assertEqual(
            thumbnail(self._build_png_file('sample-tall.png'),
                      storage=self.storage,
                      size=(300, None)),
            '/media/sample-tall_300.png')

        self._check_image_size(name='sample-tall_300.png',
                               expected_width=300,
                               expected_height=450)

    def test_with_size_tuple_height_only(self) -> None:
        """Testing {% thumbnail %} with size as tuple and height only"""
        self.assertEqual(
            thumbnail(self._build_png_file('sample-tall.png'),
                      storage=self.storage,
                      size=(None, 200)),
            '/media/sample-tall_x200.png')

        self._check_image_size(name='sample-tall_x200.png',
                               expected_width=133,
                               expected_height=200)

    def test_with_size_tuple_invalid(self) -> None:
        """Testing {% thumbnail %} with size as invalid tuple"""
        message = "Thumbnail size (None, None) is not valid."

        with self.assertRaisesMessage(ValueError, message):
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=(None, None))

    def test_with_size_invalid(self) -> None:
        """Testing {% thumbnail %} with size as invalid type"""
        message = "Thumbnail size 300 is not valid."

        with self.assertRaisesMessage(ValueError, message):
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=300)  # type: ignore

    def test_with_existing(self) -> None:
        """Testing {% thumbnail %} with existing thumbnail in storage"""
        path = os.path.join(self._storage_root, 'sample-wide_300x250.png')

        with open(path, 'wb') as fp:
            fp.write(b'...\n')

        self.assertEqual(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=(300, 250)),
            '/media/sample-wide_300x250.png')

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), b'...\n')

    def test_with_existing_and_create_if_missing_false(self) -> None:
        """Testing {% thumbnail %} with existing thumbnail in storage and
        create_if_missing_false"""
        path = os.path.join(self._storage_root, 'sample-wide_300x250.png')

        with open(path, 'wb') as fp:
            fp.write(b'...\n')

        self.assertEqual(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=(300, 250),
                      create_if_missing=False),
            '/media/sample-wide_300x250.png')

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), b'...\n')

    def test_with_missing_and_create_if_missing_false(self) -> None:
        """Testing {% thumbnail %} with missing thumbnail in storage and
        create_if_missing_false"""
        self.assertIsNone(
            thumbnail(self._build_png_file('sample-wide.png'),
                      storage=self.storage,
                      size=(300, 250),
                      create_if_missing=False))

        self.assertFalse(os.path.exists(
            os.path.join(self._storage_root, 'sample-wide_300x250.png')))

    def _build_png_file(
        self,
        name: str,
    ) -> File:
        """Create a PNG file and return an instance to it.

        Args:
            name (str):
                The name of the testdata image file to copy and return.

        Returns:
            django.core.files.base.File:
            The file instance for that file.
        """
        src_filename = os.path.abspath(os.path.join(
            __file__, '..', 'testdata', name))
        dest_filename = os.path.abspath(os.path.join(
            self._storage_root, name))

        shutil.copy(src_filename, dest_filename)

        return File(name=name,
                    file=None)

    def _check_image_size(
        self,
        *,
        name: str,
        expected_width: int,
        expected_height: int,
    ) -> None:
        """Check the resulting size of a thumbnail image.

        Args:
            name (str):
                The name of the thumbnail file.

            expected_width (int):
                The expected width of the thumbnail.

            expected_height (int):
                The expected height of the thumbnail.

        Raises:
            AssertionError:
                One of the expectations failed.
        """
        path = os.path.join(self._storage_root, name)
        self.assertTrue(os.path.exists(path))

        with open(path, 'rb') as fp:
            image = Image.open(io.BytesIO(fp.read()))

        self.assertEqual(image.width, expected_width)
        self.assertEqual(image.height, expected_height)
