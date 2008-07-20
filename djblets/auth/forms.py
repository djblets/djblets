from django import forms
from django.contrib import auth

from djblets.auth.util import get_user


class RegistrationForm(forms.Form):
    """Registration form that should be appropriate for most cases."""

    username = forms.RegexField(r"^[a-zA-Z0-9_\-\.]*$",
                                max_length=30,
                                error_message='Only A-Z, 0-9, "_", "-", and "." allowed.')
    password1 = forms.CharField(min_length=5,
                                max_length=30,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField()

    def clean_password2(self):
        # XXX Compatibility with Django 0.96 and 1.0
        formdata = getattr(self, "cleaned_data",
                           getattr(self, "clean_data", None))

        if 'password1' in formdata:
            if formdata['password1'] != formdata['password2']:
                raise forms.ValidationError('Passwords must match')
        return formdata['password2']

    def save(self):
        if not self.errors:
            # XXX Compatibility with Django 0.96 and 1.0
            formdata = getattr(self, "cleaned_data",
                               getattr(self, "clean_data", None))

            d = dict((k, v.encode("utf8")) for k, v in formdata.iteritems())
            try:
                user = auth.models.User.objects.create_user(d['username'],
                                                            d['email'],
                                                            d['password1'])
                return user
            except:
                # We check for duplicate users here instead of clean, since it's
                # possible that two users could race for a name.
                if get_user(username=d['username']):
                    self.errors['username'] = \
                        forms.util.ErrorList(["Sorry, this username is taken."])
                else:
                    raise


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password1 = forms.CharField(min_length=5,
                                    max_length=30,
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_new_password2(self):
        # XXX Compatibility with Django 0.96 and 1.0
        formdata = getattr(self, "cleaned_data",
                           getattr(self, "clean_data", None))

        if 'new_password1' in formdata:
            if formdata['new_password1'] != formdata['new_password2']:
                raise forms.ValidationError('Passwords must match')
            return formdata['new_password2']


class ChangeProfileForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(min_length=5, max_length=30,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_password2(self):
        # XXX Compatibility with Django 0.96 and 1.0
        formdata = getattr(self, "cleaned_data",
                           getattr(self, "clean_data", None))

        if 'password1' in formdata:
            if formdata['password1'] != formdata['password2']:
                raise forms.ValidationError('Passwords must match')
        return formdata['password2']

