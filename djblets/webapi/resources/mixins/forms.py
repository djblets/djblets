"""Mixins for integrating a web API resource with a form."""

from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.models import model_to_dict
from django.utils import six
from django.utils.encoding import force_text

from djblets.webapi.errors import INVALID_FORM_DATA


class UpdateFormMixin(object):
    """A mixin for providing the ability to create and update using a form.

    A WebAPIResource class using this mixin must set the :py:attr:`form_class`
    attribute to a :py:class:`~django.forms.ModelForm` instance that
    corresponds to the model being updated.

    Classes using this mixin can provide methods of the form
    :samp:`parse_{field_name}_field` to do parsing of form data before it is
    passed to the form. Parser methods should be of the form:

    .. code-block:: python

      def parse_some_field(self, value, request, **kwargs):
          return some_value

    These methods may return either a single value or a list of values (in
    the case where the corresponding field expects a list of values, such as a
    :py:class:`~django.forms.ModelMultipleChoiceField`). They may also raise a
    :py:class:`~django.core.exceptions.ValidationError`, though it's up to the
    caller of :py:meth:`create_form` to catch this and return any suitable
    errors.

    Most implementations will want to call :py:meth:`handle_form_request` in
    their POST/PUT handlers, and override behavior with the parsing methods.
    Some may also want to override :py:meth:`save_form`,
    :py:meth:`build_form_success_response`, or
    :py:meth:`build_form_error_response` to customize behavior.
    """

    #: The form class for updating models.
    #:
    #: This should be a subclass of :py:class:`django.forms.ModelForm`.
    form_class = None

    @property
    def add_form_class(self):
        """The form class for creating new models.

        This should be a subclass of :py:class:`django.forms.ModelForm`. It
        defaults to :py:attr:`form_class`.
        """
        return self.form_class

    def handle_form_request(self, request, data=None, files=None,
                            instance=None, form_kwargs=None,
                            save_kwargs=None, **kwargs):
        """Handle an HTTP request for creating or updating through a form.

        This can be called directly from a resource's
        :py:meth:`~djblets.webapi.resources.base.WebAPIResource.create` or
        :py:meth:`~djblets.webapi.resources.base.WebAPIResource.update` method
        to parse request data, create the form, and handle errors or the
        saving of the form.

        Version Added:
            1.0.9

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            data (dict, optional):
                The data to pass to :py:meth:`create_form`.

            files (dict, optional):
                Files to pass to the form.

            instance (django.db.models.Model, optional):
                An existing instance to update, if performing an HTTP PUT
                request.

            form_kwargs (dict, optional):
                Keyword arguments to pass to the form's constructor.

            save_kwargs (dict, optional):
                Keyword arguments to pass to the form's
                :py:meth:`ModelForm.save() <django.forms.ModelForm.save>`
                method.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`build_form_error_response`,
                :py:meth:`build_form_success_response`,
                :py:meth:`create_form`,
                :py:meth:`save_form`, and any field parsing methods.

        Returns:
            tuple or django.http.HttpResponse:
            The response to send back to the client.
        """
        is_created = instance is None

        try:
            form = self.create_form(instance=instance,
                                    data=data,
                                    files=files,
                                    request=request,
                                    form_kwargs=form_kwargs,
                                    **kwargs)
        except ValidationError as e:
            return self.build_form_error_response(errors=e,
                                                  instance=instance,
                                                  **kwargs)

        if not form.is_valid():
            return self.build_form_error_response(form=form,
                                                  instance=instance,
                                                  **kwargs)

        instance = self.save_form(form=form,
                                  save_kwargs=save_kwargs,
                                  **kwargs)

        return self.build_form_success_response(form=form,
                                                instance=instance,
                                                is_created=is_created,
                                                **kwargs)

    def create_form(self, data, request, files=None, instance=None,
                    form_kwargs=None, **kwargs):
        """Create a new form and pre-fill it with data.

        Version Changed:
            1.0.9:
            The initial values for form fields are now automatically provided
            in the form data, if not otherwise overridden, making it easier to
            construct forms.

            Along with this, a :py:class:`~django.forms.ModelForm`'s ``fields``
            and ``exclude`` lists are now factored in when populating the formw
            with an instance's data.

        Args:
            data (dict):
                The request data to pass to the form.

            request (django.http.HttpRequest):
                The HTTP request.

            files (dict):
                Files to pass to the form.

            instance (django.db.models.Model, optional):
                The instance model, if it exists. If this is not ``None``,
                fields that appear in the form class's ``fields`` attribute
                that do not appear in the ``data`` dict as keys will be copied
                from the instance.

            form_kwargs (dict, optional):
                Additional keyword arguments to provide to the form's
                constructor.

            **kwargs (dict):
                Additional arguments. These will be passed to the resource's
                parser methods.

                This contains anything passed as keyword arguments to
                :py:meth:`handle_form_request`.

        Returns:
            django.forms.ModelForm:
            The form with data filled.

        Raises:
            django.core.exceptions.ValidationError:
                A field failed validation. This is allowed to be raised by
                any ``parse_*`` methods defined on the resource.
        """
        assert self.form_class, ('%s must define a form_class attribute.'
                                 % self.__class__.__name__)

        if instance is not None:
            form_cls = self.form_class
        else:
            form_cls = self.add_form_class

        form_data = self._get_initial_form_data(form_cls)

        if instance is not None:
            meta = form_cls._meta
            form_data.update(model_to_dict(instance=instance,
                                           fields=meta.fields,
                                           exclude=meta.exclude))

        form_data.update(self._parse_form_data(data, request, **kwargs))

        # Dynamically provide the arguments we want to the form, so that
        # any form classes lacking an argument (files, for instance) won't
        # result in a crash so long as the equivalent argument is not provided.
        if form_kwargs is None:
            form_kwargs = {}
        else:
            form_kwargs = form_kwargs.copy()

        if form_data is not None:
            form_kwargs['data'] = form_data

        if files is not None:
            form_kwargs['files'] = files

        if instance is not None:
            form_kwargs['instance'] = instance

        return form_cls(**form_kwargs)

    def save_form(self, form, save_kwargs=None, **kwargs):
        """Save and return the results of the form.

        This is a simple wrapper around calling :py:meth:`ModelForm.save()
        <django.forms.ModelForm.save>`. It can be overridden by subclasses
        that need to perform additional operations on the instance or form.

        Version Added:
            1.0.9

        Args:
            form (django.forms.Form):
                The form to save.

            save_kwargs (dict):
                Any keyword arguments to pass when saving the form.

            **kwargs (dict):
                Additional keyword arguments passed by the caller. This
                contains anything passed as keyword arguments to
                :py:meth:`handle_form_request`.

        Returns:
            django.db.models.Model:
            The saved model instance.
        """
        return form.save(**(save_kwargs or {}))

    def build_form_errors(self, form=None, errors=None, **kwargs):
        """Return a dictionary of field errors for use in a response payload.

        This will convert each error to a string, resulting in a dictionary
        mapping field names to lists of errors. This can be safely returned in
        any API payload.

        Version Added:
            1.0.9

        Args:
            form (django.forms.Form, optional):
                The form containing errors. This may be ``None`` if handling
                a :py:class:`~django.core.exceptions.ValidationError` from
                field parsing.

            errors (django.core.exceptions.ValidationError, optional):
                An explicit validation error to use for the payload. This will
                be used if field parsing fails.

            **kwargs (dict):
                Additional keyword arguments passed by the caller. This
                contains anything passed as keyword arguments to
                :py:meth:`handle_form_request`.

        Returns:
            dict:
            The dictionary of errors. Each key is a field name and each
            value is a list of error strings.
        """
        assert (form is None) != (errors is None), \
            'Only one of form or errors can be provided.'

        if form is not None:
            return {
                field_name: [force_text(e) for e in field_errors]
                for field_name, field_errors in six.iteritems(form.errors)
            }
        else:
            if hasattr(errors, 'error_dict'):
                return errors.message_dict
            else:
                return {
                    NON_FIELD_ERRORS: errors.messages,
                }

    def build_form_success_response(self, form, instance, is_created,
                                    **kwargs):
        """Return a success response for a saved instance.

        Version Added:
            1.0.9

        Args:
            form (django.forms.Form):
                The form that saved the instance.

            instance (django.db.models.Model):
                The saved instance.

            is_created (bool):
                Whether the instance was created.

            **kwargs (dict):
                Additional keyword arguments passed by the caller. This
                contains anything passed as keyword arguments to
                :py:meth:`handle_form_request`.

        Returns:
            tuple or django.http.HttpResponse:
            The success response to return from the API handler.
        """
        if is_created:
            code = 201
        else:
            code = 200

        return code, {
            self.item_result_key: instance,
        }

    def build_form_error_response(self, form=None, errors=None, instance=None,
                                  **kwargs):
        """Return an error response containing errors for form fields.

        Version Added:
            1.0.9

        Args:
            form (django.forms.Form, optional):
                The form containing errors. This may be ``None`` if handling
                a :py:class:`~django.core.exceptions.ValidationError` from
                field parsing.

            errors (django.core.exceptions.ValidationError, optional):
                An explicit validation error to use for the payload. This will
                be used if field parsing fails.

            instance (django.db.models.Model, optional):
                The existing instance, if any.

            **kwargs (dict):
                Additional keyword arguments passed by the caller. This
                contains anything passed as ``response_kwargs`` to
                :py:meth:`handle_form_request`.

        Returns:
            tuple or django.http.HttpResponse:
            The error response to return from the API handler.
        """
        return INVALID_FORM_DATA, {
            'fields': self.build_form_errors(form=form,
                                             errors=errors),
        }

    def _get_initial_form_data(self, form_cls):
        """Return the initial data for a form.

        This will return the initial data from all fields in a form,
        converting each into a format suitable for passing as bound data
        for a form.

        Args:
            form_cls (type):
                The form's class.

        Returns:
            dict:
            The initial data for the fields in the form.
        """
        initial = {}

        for field_name, field in six.iteritems(form_cls.base_fields):
            data = field.initial

            if callable(data):
                data = data()

            initial[field_name] = data

        return initial

    def _parse_form_data(self, form_data, request, **kwargs):
        """Parse the form data.

        Args:
            form_data (dict):
                The request data.

            request (django.http.HttpRequest):
                The HTTP request.

            **kwargs (dict):
                Additional arguments to pass to parser methods.

        Returns:
            dict:
            A mapping of field names to parsed values.

        Raises:
            django.core.exceptions.ValidationError:
                A field failed validation containing errors for any fields
                that failed to parse.
        """
        parsed_data = form_data.copy()
        errors = {}

        for field, value in six.iteritems(form_data):
            parser = getattr(self, 'parse_%s_field' % field, None)

            if parser is not None:
                try:
                    parsed_data[field] = parser(value, request=request,
                                                **kwargs)
                except ValidationError as e:
                    errors[field] = e.messages
            else:
                parsed_data[field] = value

        if errors:
            raise ValidationError(errors)

        return parsed_data
