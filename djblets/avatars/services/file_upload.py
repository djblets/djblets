"""An avatar service for providing uploaded images."""

from __future__ import unicode_literals

import os
from hashlib import md5
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import DefaultStorage
from django.forms import forms, widgets
from django.utils.translation import ugettext_lazy as _

from djblets.avatars.forms import AvatarServiceConfigForm
from djblets.avatars.services.base import AvatarService


class FileUploadServiceForm(AvatarServiceConfigForm):
    """The FileUploadService configuration form."""

    avatar_service_id = 'file-upload'

    js_view_class = 'Djblets.Avatars.FileUploadSettingsFormView'
    template_name = 'avatars/services/file_upload_form.html'

    avatar_upload = forms.FileField(
        required=True,
        widget=widgets.FileInput(attrs={
            'accept': 'image/png, image/jpeg, image/gif',
        }))

    MAX_FILE_SIZE = 1 * 1024 * 1024
    is_multipart = True

    def clean_file(self):
        """Ensure the uploaded file is an image of an appropriate size.

        Returns:
            django.core.files.UploadedFile:
            The uploaded file, if it is valid.

        Raises:
            django.core.exceptions.ValidationError:
                Raised if the file is too large or the incorrect MIME type.
        """
        f = self.cleaned_data['avatar_upload']

        if f.size > self.MAX_FILE_SIZE:
            raise ValidationError(_('The file is too large.'))

        content_type = f.content_type.split('/')[0]

        if content_type != 'image':
            raise ValidationError(_('Only images are supported.'))

        return f

    def save(self):
        """Save the file and return the configuration.

        Returns:
            dict:
            The avatar service configuration.
        """
        storage = DefaultStorage()
        username = self.user.username

        uploaded_file = self.cleaned_data['avatar_upload']
        file_hash = md5()

        for chunk in uploaded_file.chunks():
            file_hash.update(chunk)

        # In the case where the filename does not have an extension,
        # splitext(filename) will return (filename, '').
        file_path = storage.get_valid_name(
            '%s%s'
            % (self.service.get_unique_filename(username),
               os.path.splitext(self.cleaned_data['avatar_upload'].name)[1])
        )

        file_path = os.path.join(username[0], username[:2], file_path)

        if self.service.file_path_prefix:
            file_path = os.path.join(self.service.file_path_prefix,
                                     file_path)

        file_path = storage.save(file_path, uploaded_file)

        return {
            'file_path': file_path,
            'file_hash': file_hash.hexdigest(),
        }


class FileUploadService(AvatarService):
    """An avatar service for uploaded images."""

    avatar_service_id = 'file-upload'
    name = _('File Upload')

    config_form_class = FileUploadServiceForm

    @property
    def file_path_prefix(self):
        """The storage location for uploaded avatars.

        This will be prepended to the path of all uploaded files. By default,
        it is controlled by the :setting:`UPLOADED_AVATARS_PATH` setting.
        """
        return getattr(settings, 'UPLOADED_AVATARS_PATH',
                       os.path.join('uploaded', 'avatars'))

    def get_unique_filename(self, filename):
        """Create a unique filename.

        The unique filename will be the original filename suffixed with a
        generated UUID.

        Args:
            filename (unicode):
                The filename, excluding the extension.

        Returns:
            unicode:
            The unique filename.
        """
        return '%s__%s' % (filename, uuid4())

    def get_avatar_urls_uncached(self, user, size):
        """Return the avatar URLs for the requested user.

        Args:
            user (django.contrib.auth.models.User):
                The user whose avatar URLs are to be fetched.

            size (int):
                The size (in pixels) the avatar is to be rendered at.

        Returns
            dict:
            A dictionary containing the URLs of the user's avatars at normal-
            and high-DPI.
        """
        storage = DefaultStorage()
        settings_manager = self._settings_manager_class(user)
        configuration = \
            settings_manager.configuration_for(self.avatar_service_id)

        if not configuration:
            return {}

        return {
            '1x': storage.url(configuration['file_path'])
        }

    def cleanup(self, user):
        """Clean up the uploaded file.

        This will delete the uploaded file from the storage.

        Args:
            user (django.contrib.auth.models.User):
                The user.
        """
        settings_manager = self._settings_manager_class(user)
        configuration = settings_manager.configuration_for(
            self.avatar_service_id)

        try:
            del configuration['file_hash']
        except KeyError:
            pass

        settings_manager.save()

        storage = DefaultStorage()
        storage.delete(configuration['file_path'])

    def get_etag_data(self, user):
        """Return the ETag data for the user's avatar.

        Args:
            user (django.contrib.auth.models.User):
                The user.

        Returns:
            list of unicode:
            The uniquely identifying information for the user's avatar.
        """
        settings_manager = self._settings_manager_class(user)
        configuration = \
            settings_manager.configuration_for(self.avatar_service_id)

        file_hash = configuration.get('file_hash')

        if not file_hash:
            storage = DefaultStorage()
            file_hash = md5()

            with storage.open(configuration['file_path'], 'rb') as f:
                file_hash.update(f.read())

            configuration['file_hash'] = file_hash.hexdigest()
            settings_manager.save()

        return [self.avatar_service_id, file_hash]
