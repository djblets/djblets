#
# forms.py -- Forms for authentication
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
#
"""Common forms for authentication tasks.

These forms can be used either directly or as a base for more specific forms.
They're designed to take some of the complexity out of creating
authentication-related forms not otherwise provided by Django.
"""

from __future__ import unicode_literals

from django import forms
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from djblets.db.query import get_object_or_none


try:
    # Django renamed forms.util to forms.utils in 1.7.
    from django.forms import utils as form_utils
except ImportError:
    from django.forms import util as form_utils


class RegistrationForm(forms.Form):
    """A standard registration form collecting basic account information.

    This form prompts the user for a username, a password (and a confirmation
    on that password), e-mail address, first name, and last name. It then
    validates these, attempting to create a :py:class:`User`.

    This class can be extended by subclasses to provide additional fields.
    """

    username = forms.RegexField(
        r"^[a-zA-Z0-9_\-\.]*$",
        max_length=30,
        error_message='Only A-Z, 0-9, "_", "-", and "." allowed.')
    password1 = forms.CharField(label=_('Password'),
                                min_length=5,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Password (confirm)'),
                                widget=forms.PasswordInput)
    email = forms.EmailField(label=_('E-mail address'))
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    def __init__(self, request=None, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_password2(self):
        """Validate that the two supplied passwords match.

        If they do not match, validation will fail, and an error will be
        supplied to the user.

        Returns:
            str: The password supplied on the form.

        Raises:
            ValidationError: If the passwords do not match.
        """
        formdata = self.cleaned_data
        if 'password1' in formdata:
            if formdata['password1'] != formdata['password2']:
                raise ValidationError(_('Passwords must match'))
        return formdata['password2']

    def save(self):
        """Save the form, creating a user if validation passes.

        The :py:class:`User` will be created with the provided username,
        e-mail address, password, and full name. If there are failures
        in creating this user, or there's an existing user with the given
        name, an error will be raisd.

        Subclasses that want to override this can call the parent's
        py:meth:`save` and modify the resulting user, if ``None`` is not
        returned.

        Returns:
            User: The newly-created user.
        """
        if not self.errors:
            try:
                user = auth.models.User.objects.create_user(
                    self.cleaned_data['username'],
                    self.cleaned_data['email'],
                    self.cleaned_data['password1'])
                user.first_name = self.cleaned_data['first_name']
                user.last_name = self.cleaned_data['last_name']
                user.save()
                return user
            except:
                # We check for duplicate users here instead of clean, since
                # it's possible that two users could race for a name.
                if get_object_or_none(User,
                                      username=self.cleaned_data['username']):
                    self.errors['username'] = form_utils.ErrorList(
                        [_('Sorry, this username is taken.')])
                else:
                    raise
