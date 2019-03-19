"""Djblets Avatar Services."""

from __future__ import unicode_literals

from djblets.avatars.services.base import AvatarService
from djblets.avatars.services.fallback import FallbackService
from djblets.avatars.services.file_upload import FileUploadService
from djblets.avatars.services.gravatar import GravatarService
from djblets.avatars.services.url import URLAvatarService


__all__ = (
    'AvatarService',
    'FallbackService',
    'FileUploadService',
    'GravatarService',
    'URLAvatarService',
)
