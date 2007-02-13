from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import signals
from django.dispatch import dispatcher
import os, re, Image

# These must be listed from largest to smallest
THUMBNAIL_SIZES = (256, 128, 64, 32, 16)


class ImageSource(models.Model):
    """This table provides each immutable image with a unique ID
       number, and it provides metadata about the source of that
       image. Every image with the same ImageSource should be identical
       aside from format or resolution differences.
       """
    is_temporary = models.BooleanField(default=True)
    reviewed_by_admin = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def create_path(self, suffix, extension=".png"):
        id_dirs = "/".join(re.findall("..?", "%x" % self.id))
        return "".join((id_dirs, suffix, extension))

    def get_thumbnail(self, size=128):
        return self.instances.get(thumbnail_size = size)

    def get_original(self):
        return self.instances.get(is_original = True)

    def reference(self):
        """Inform this image that it's been referenced permanently.
           This clears the is_temporary flag and saves, if necessary.
           """
        if self.is_temporary:
            self.is_temporary = False
            self.save()

    def to_html(self):
        # Currently this is used only by the change history browser.
        return self.get_thumbnail(size=64).to_html()

    def __str__(self):
        original = self.get_original()
        s = "Image #%d (%dx%d)" % (self.id, original.width, original.height)
        if self.is_temporary:
            s += " (temp)"
        return s

class ImageInstanceManager(models.Manager):
    def create_from_image(self, image, source, suffix="", **kw):
        """Create an image instance from a PIL image, using
           the provided path suffix.
           """
        path = source.create_path(suffix)
        i = ImageInstance(source = source,
                          path = path,
                          width = image.size[0],
                          height = image.size[1],
                          **kw)
        i.store_image(image)
        i.save()

    def create_original(self, image, created_by, is_temporary=True):
        """Create an original image from uploaded data, given a PIL
           Image object. The resulting image will always be saved as
           a PNG file. Automatically creates all default thumbnail sizes.

           Returns the new ImageSource instance.
           """
        source = ImageSource.objects.create(created_by=created_by,
                                            is_temporary=is_temporary)
        self.create_from_image(image, source, is_original=True)
        self.create_standard_thumbnails(image, source)
        return source

    def create_standard_thumbnails(self, image, source):
        """Warning, may modify the input image!"""

        if image.mode not in ('RGB', 'RGBA', 'L'):
            image = image.convert("RGBA")

        # To save time, first scale the original image down
        # to the largest of the thumbnail sizes. This doesn't
        # sacrifice much quality, but it greatly improves memory
        # and CPU usage when thumbnailing big images.

        max_size = THUMBNAIL_SIZES[0]
        if max(*image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.ANTIALIAS)

        for size in THUMBNAIL_SIZES:
            self.create_thumbnail(image, source, size)

    def create_thumbnail(self, image, source, size):
        """Create a thumbnail at the specified size."""

        # If the image is already small enough, we can skip the
        # actual thumbnailing stage and just link back to the
        # original image.
        original = source.get_original()
        if max(original.width, original.height) <= size:
            return ImageInstance.objects.create(source = source,
                                                path = original.path,
                                                width = original.width,
                                                height = original.height,
                                                delete_file = False,
                                                thumbnail_size = size)

        if image.mode not in ('RGB', 'RGBA', 'L'):
            image = image.convert("RGBA")

        # Our thumbnails look much better if we paste the image into
        # a larger transparent one first with a margin about equal to one
        # pixel in our final thumbnail size. This smoothly blends
        # the edge of the image to transparent rather than chopping
        # off a fraction of a pixel. It looks, from experimentation,
        # like this margin is only necessary on the bottom and right
        # sides of the image.

        margins = (image.size[0] // size + 1,
                   image.size[1] // size + 1)
        bg = Image.new("RGBA",
                       (image.size[0] + margins[0],
                        image.size[1] + margins[1]),
                       (255, 255, 255, 0))
        bg.paste(image, (0,0))
        bg.thumbnail((size, size), Image.ANTIALIAS)
        return self.create_from_image(bg, source, "-t%d" % size, thumbnail_size=size)


class ImageInstance(models.Model):
    """An image file representing a source image in a particular
       size. The size is cached. The image itself is stored in the CIA
       flat-file database, and served by the static file server.
       """
    objects = ImageInstanceManager()

    source = models.ForeignKey(ImageSource, related_name='instances')

    is_original = models.BooleanField(default=False)
    thumbnail_size = models.PositiveIntegerField(null=True, blank=True)

    path = models.CharField(maxlength=32)
    delete_file = models.BooleanField(default=True)

    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()

    def get_url(self):
        return '/images/db/' + self.path

    def get_path(self):
        return os.path.join(settings.CIA_DATA_PATH, 'db', 'images' , self.path)

    def store_image(self, im):
        full_path = self.get_path()
        directory = os.path.dirname(full_path)
        try:
            os.makedirs(directory)
        except OSError:
            pass
        im.save(full_path)

    def to_html(self):
        return '<img src="%s" width="%d" height="%d" />' % (
            self.get_url(), self.width, self.height)

def remove_deleted_instance(instance):
    if instance.delete_file:
        try:
            os.unlink(instance.get_path())
        except OSError:
            pass

dispatcher.connect(remove_deleted_instance, signal=signals.post_delete, sender=ImageInstance)
