#
# authplus.py
#
# Copyright (C) 2007 David Trowbridge
# Copyright (C) 2007 Micah Dowty
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from django import newforms as forms
from django.conf import settings
from django.contrib import auth
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.shortcuts import render_to_response
from django.template import loader
from django.template.context import RequestContext, Context

from djblets.util.decorators import simple_decorator

import datetime, re

###########################
#    Utility functions    #
###########################

@simple_decorator
def login_required(view_func):
    """Simplified version of auth.decorators.login_required,
       which works with our LOGIN_URL and removes the 'next'
       parameter which we don't need yet.
       """
    def _checklogin(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(settings.LOGIN_URL)
    return _checklogin

def get_user(username):
    try:
        return auth.models.User.objects.get(username=username)
    except auth.models.User.DoesNotExist:
        return None

def internal_login(request, username, password):
    user = auth.authenticate(username=username, password=password)
    if user is None:
        return "Incorrect username or password."
    elif not user.is_active:
        return "This account is inactive."
    elif not request.session.test_cookie_worked():
        return "Cookies must be enabled."

    auth.login(request, user)
    request.session.delete_test_cookie()
    user.last_login = datetime.datetime.now()
    user.save()

def validate_test_cookie(form, request):
    if not request.session.test_cookie_worked():
        form.errors['submit'] = forms.util.ErrorList(["Cookies must be enabled."])

###########################
#       User Login        #
###########################

def login(request, next_page, template_name="accounts/login.html"):
    """Simple login form view which doesn't rely on Django's current
       inflexible oldforms-based auth view.
       """
    if request.POST:
        error = internal_login(request,
                               request.POST.get('username'),
                               request.POST.get('password'))
        if not error:
            return HttpResponseRedirect(next_page)
    else:
        error = None

    request.session.set_test_cookie()
    return render_to_response(template_name, RequestContext(request, {
        'error' : error,
        'login_url' : settings.LOGIN_URL,
        }))

###########################
#    User Registration    #
###########################

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
        if 'password1' in self.clean_data:
            if self.clean_data['password1'] != self.clean_data['password2']:
                raise forms.ValidationError('Passwords must match')
        return self.clean_data['password2']

    def save(self):
        if not self.errors:
            d = dict((k, v.encode("utf8")) for k, v in self.clean_data.iteritems())
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

def register(request, template_name="accounts/register.html"):
    redirect_to = request.REQUEST.get(auth.REDIRECT_FIELD_NAME, '')

    if request.POST:
        form = RegistrationForm(request.POST)
        form.full_clean()
        validate_text_cookie(form, request)

        if form.is_valid():
            user = form.save()
            if user:
                user = auth.authenticate(username=form.clean_data['username'],
                                         password=form.clean_data['password1'])
                assert user
                auth.login(request, user)
                request.session.delete_test_cookie()

                if not redirect_to or '://' in redirect_to or ' ' in redirect_to:
                    redirect_to = '/account/'
                return HttpResponseRedirect(redirect_to)
    else:
        form = RegistrationForm()

    request.session.set_test_cookie()
    return render_to_response(template_name, RequestContext(request, {'form': form}))

###########################
#     Profile Editing     #
###########################

class ChangePasswordForm(forms.Form):
    old_password = forms.CharField()
    new_password = forms.CharField(min_length=5, max_length=30)
    new_password2 = forms.CharField()

def do_change_password(request):
    form = ChangePasswordForm(request.POST)
    form.full_clean()
    validate_password_confirmation(form, 'new_password')
    validate_old_password(form, request.user, 'old_password')
    if not form.errors:
        request.user.set_password(form.clean_data['new_password'])
        request.user.save()
        request.user.message_set.create(message="Your password was changed successfully.")
    return form

class ChangeProfileForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()

def do_change_profile(request):
    form = ChangeProfileForm(request.POST)
    form.full_clean()
    if not form.errors:
        for key, value in form.clean_data.items():
            setattr(request.user, key, value)
        request.user.save()
        request.user.message_set.create(message="Your profile was updated successfully.")
    return form

###########################
#     Lost Password       #
###########################

def send_mail_to_user(user, template_name, **context_dict):
    """Send a single email message to a registered user. This formats their
       email address using their full name, and automatically treats the
       first non-blank line of the rendered template as a message subject.

       The template context will automatically include 'user'.
       """
    context = Context(context_dict)
    context['user'] = user
    subject, message = loader.render_to_string(template_name, context).lstrip().split("\n", 1)
    subject = subject.strip()
    message = message.strip()

    # Sanitize the user's name for inclusion in an RFC822 header
    full_name = re.sub("[!<>@:;\\\\'\"\[\]\r\n\t]", "", user.get_full_name().strip())
    send_mail(subject, message, None, ["%s <%s>" % (full_name, user.email)])

def lost(request, next_page, recovery_page,
         mail_template_name='accounts/recovery_mail.txt',
         form_template_name='accounts/recovery_form.html',
         sent_template_name='accounts/recovery_mail_sent.html'):
    error = None
    if request.POST:
        user = get_user(request.POST.get('username'))
        if not user:
            error = "Incorrect username."
        if not error:
            # Password recovery works via a special kind of session
            # which is transmitted over e-mail, rather than via a
            # cookie. Create a session which includes the username
            # this request was generated for.

            key = Session.objects.get_new_session_key()
            expire_date = datetime.datetime.now() + datetime.timedelta(hours=12)
            Session.objects.save(key, {
                'account_recovery_session': True,
                'username': user.username,
                }, expire_date)

            send_mail_to_user(user, mail_template_name,
                              request = request,
                              recovery_path = recovery_page % key)
            return render_to_response(sent_template_name)
    return render_to_response(form_template_name, RequestContext(request, {'error': error}))

def get_recovery_session(key):
    """Get an account recovery session, with extra checks to make sure
       it's the right type of session and it hasn't expired.
       """
    try:
        session = Session.objects.get(session_key=key)
    except Session.DoesNotExist:
        return None

    if session.expire_date < datetime.datetime.now():
        return None

    decoded = session.get_decoded()
    if not decoded.get('account_recovery_session'):
        return None
    return decoded

class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(min_length=5, max_length=30,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_password2(self):
        if 'password1' in self.clean_data:
            if self.clean_data['password1'] != self.clean_data['password2']:
                raise forms.ValidationError('Passwords must match')
        return self.clean_data['password2']

def reset(request, key, next_page,
          form_template_name='accounts/reset_password.html',
          error_template_name='accounts/recovery_key_error.html'):
    session = get_recovery_session(key)
    if not session:
        return render_to_response(error_template_name, RequestContext(request))
    user = get_user(session.get('username'))

    if request.POST:
        form = ResetPasswordForm(request.POST)
        form.full_clean()
        validate_test_cookie(form, request)

        if not form.errors:
            user.set_password(form.clean_data['password1'])
            user.save()

            # Try to log in using the new password
            loginError = internal_login(request, user.username, form.clean_data['password1'])
            if loginError:
                # This might happen if the account is deactivated.
                form.errors['submit'] = forms.util.ErrorList([loginError])
            else:
                # We're in successfully. Expire the recovery session.
                Session.objects.save(key, None, datetime.datetime.now())
                return HttpResponseRedirect(next_page)
    else:
        form = None

    request.session.set_test_cookie()
    return render_to_response(form_template_name, RequestContext(request, {
        'form_path': request.path,
        'username': user.username,
        'form': form,
        }))

