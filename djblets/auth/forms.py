"""Common forms for authentication tasks.

These forms can be used either directly or as a base for more specific forms.
They're designed to take some of the complexity out of creating
authentication-related forms not otherwise provided by Django.
"""

from __future__ import unicode_literals

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _


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
        error_messages={
            'invalid': _('Only A-Z, 0-9, "_", "-", and "." are allowed.'),
        })
    password1 = forms.CharField(label=_('Password'),
                                min_length=5,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Password (confirm)'),
                                widget=forms.PasswordInput)
    email = forms.EmailField(label=_('E-mail address'))
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    def __init__(self, request=None, *args, **kwargs):
        """Initialize the form.

        Args:
            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_password2(self):
        """Validate that the two supplied passwords match.

        If they do not match, validation will fail, and an error will be
        supplied to the user.

        Returns:
            unicode:
            The password supplied on the form.

        Raises:
            django.core.exceptions.ValidationError:
                If the passwords do not match.
        """
        formdata = self.cleaned_data

        if ('password1' in formdata and
            formdata['password1'] != formdata['password2']):
            raise ValidationError(_('Passwords must match'))

        return formdata['password2']

    def save(self):
        """Save the form, creating a user if validation passes.

        The user will be created with the provided username, e-mail address,
        password, and full name. If there are failures in creating this user,
        or there's an existing user with the given name, an error will be
        raised. Creation always occurs in its own transaction, ensuring it's
        immediately saved and preventing potential lookup problems when there's
        a conflict.

        Subclasses that want to override this can call the parent's
        py:meth:`save` and modify the resulting user, if ``None`` is not
        returned.

        Returns:
            django.contrib.auth.models.User:
            The newly-created user, or ``None`` if there was a conflict when
            creating it.

        Raises:
            Exception:
                An unexpected exception occurred.
        """
        if not self.errors:
            username = self.cleaned_data['username']

            try:
                with transaction.atomic():
                    return User.objects.create_user(
                        username=username,
                        password=self.cleaned_data['password1'],
                        email=self.cleaned_data['email'],
                        first_name=self.cleaned_data['first_name'],
                        last_name=self.cleaned_data['last_name'])
            except:
                # We check for duplicate users here instead of clean, since
                # it's possible that two users could race for a name.
                if User.objects.filter(username=username).exists():
                    self.errors['username'] = self.error_class(
                        [_('Sorry, this username is taken.')])
                else:
                    raise

        return None
