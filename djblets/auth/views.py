#
# views.py -- Views for the authentication app
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
# Copyright (C) 2007 Micah Dowty
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


from django.conf import settings
from django.contrib import auth
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.http import HttpResponseRedirect

from djblets.auth.forms import RegistrationForm, ChangePasswordForm, \
                               ChangeProfileForm
from djblets.auth.util import internal_login, validate_test_cookie, \
                              validate_old_password


###########################
#       User Login        #
###########################

def login(request, next_page, template_name="accounts/login.html",
          extra_context={}):
    """Simple login form view which doesn't rely on Django's current
       inflexible oldforms-based auth view.
       """
    if request.POST:
        error = internal_login(request,
                               request.POST.get('username'),
                               request.POST.get('password'))
        if not error:
            return HttpResponseRedirect(request.REQUEST.get("next_page",
                                                            next_page))
    else:
        error = None

    request.session.set_test_cookie()
    context = RequestContext(request, {
        'error' : error,
        'login_url' : settings.LOGIN_URL,
        'next_page' : request.REQUEST.get("next_page", next_page)
    })

    if extra_context is not None:
        # Copied from Django's generic views.
        # The reason we don't simply call context.update(extra_context) is
        # that there are times when you may want to pass a function in the
        # URL handler that you want called at the time of render, rather than
        # being forced to expose it as a template tag or calling it upon
        # URL handler creation (which may be too early and only happens once).
        for key, value in extra_context.items():
            if callable(value):
                context[key] = value()
            else:
                context[key] = value

    return render_to_response(template_name, context)

###########################
#    User Registration    #
###########################

def register(request, next_page, form_class=RegistrationForm,
             extra_context={},
             template_name="accounts/register.html"):
    if request.POST:
        form = form_class(data=request.POST, request=request)
        form.full_clean()
        validate_test_cookie(form, request)

        if form.is_valid():
            user = form.save()
            if user:
                # XXX Compatibility with Django 0.96 and 1.0
                formdata = getattr(form, "cleaned_data",
                                   getattr(form, "clean_data", None))
                user = auth.authenticate(username=formdata['username'],
                                         password=formdata['password1'])
                assert user
                auth.login(request, user)
                try:
                    request.session.delete_test_cookie()
                except KeyError:
                    # Do nothing
                    pass

                return HttpResponseRedirect(next_page)
    else:
        form = form_class(request=request)

    request.session.set_test_cookie()

    context = {
        'form': form,
    }
    context.update(extra_context)

    return render_to_response(template_name, RequestContext(request, context))

###########################
#     Profile Editing     #
###########################

def do_change_password(request):
    form = ChangePasswordForm(request.POST)
    form.full_clean()
    validate_old_password(form, request.user, 'old_password')
    if not form.errors:
        # XXX Compatibility with Django 0.96 and 1.0
        formdata = getattr(form, "cleaned_data",
                           getattr(form, "clean_data", None))

        request.user.set_password(formdata['new_password1'])
        request.user.save()
        request.user.message_set.create(message="Your password was changed successfully.")
    return form

def do_change_profile(request):
    form = ChangeProfileForm(request.POST)
    form.full_clean()
    if not form.errors:
        # XXX Compatibility with Django 0.96 and 1.0
        formdata = getattr(form, "cleaned_data",
                           getattr(form, "clean_data", None))

        for key, value in formdata.items():
            setattr(request.user, key, value)
        request.user.save()
        request.user.message_set.create(message="Your profile was updated successfully.")
    return form
