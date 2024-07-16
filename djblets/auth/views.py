"""Authentication-related views.

The bundled views help with common authentication-related tasks not otherwise
provided by Django. At the moment, there is only support here for registration.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from django.contrib import auth
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from djblets.auth.forms import RegistrationForm
from djblets.auth.signals import user_registered
from djblets.auth.util import validate_test_cookie

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


@csrf_protect
def register(
    request: HttpRequest,
    next_page: str,
    form_class: type[RegistrationForm] = RegistrationForm,
    extra_context: Optional[dict[str, Any]] = None,
    initial_values: Optional[dict[str, Any]] = None,
    form_kwargs: Optional[dict[str, Any]] = None,
    template_name: str = 'accounts/register.html',
) -> HttpResponse:
    """Handle registration of a new user.

    This works along with :py:class:`djblets.auth.forms.RegistrationForm`
    to register a new user. It will display a registration form, validate
    the user's new information, and then log them in.

    The registration form, next page, and context can all be customized by
    the caller.

    Args:
        request (HttpRequest):
            The HTTP request from the client.

        next_page (str):
            The URL to navigate to once registration is successful.

        form_class (Form subclass):
            The form that will handle registration, field validation, and
            creation of the user.

        extra_context (dict):
            Extra context variables to pass to the template when rendering.

        initial_values (dict):
            Initial values to set on the form when it is rendered.

        form_kwargs (dict):
            Additional keyword arguments to pass to the form class during
            instantiation.

        template_name (str):
            The name of the template containing the registration form.

    Returns:
        django.http.HttpResponse:
        The page's rendered response or redirect.
    """
    if initial_values is None:
        initial_values = {}

    if form_kwargs is None:
        form_kwargs = {}

    if request.method == 'POST':
        form = form_class(data=request.POST, request=request, **form_kwargs)
        form.full_clean()
        validate_test_cookie(form, request)

        if form.is_valid():
            user = form.save()
            if user:
                user = auth.authenticate(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'])
                assert user
                auth.login(request, user)
                try:
                    request.session.delete_test_cookie()
                except KeyError:
                    # Do nothing
                    pass

                # Other components can listen to this signal to
                # perform additional tasks when a new user registers
                user_registered.send(sender=None, user=request.user)

                return HttpResponseRedirect(next_page)
    else:
        form = form_class(initial=initial_values, request=request,
                          **form_kwargs)

    request.session.set_test_cookie()

    context = {
        'form': form,
    }

    if extra_context:
        context.update(extra_context)

    return render(request, template_name, context)
