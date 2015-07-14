"""Mixins for integrating a web API resource with a form."""

from __future__ import unicode_literals

from django.forms.models import model_to_dict
from django.utils import six


class UpdateFormMixin(object):
    """A mixin for providing the ability to create and update using a form.

    A WebAPIResource class using this mixin must set the :py:attr:`form_class`
    attribute to a :py:class:`ModelForm` instance that corresponds to the model
    being updated.

    Classes using this mixin can provide methods of the form
    ``parse_<field_name>_field`` to do parsing of form data before it is passed
    to the form. Parser methods should be of the form:

    .. code-block:: python

      def parse_some_field(self, value, request, **kwargs):
          # ...

    These methods may return either a single value or a list of values (in
    the case where the corresponding field expects a list of values, such as a
    :py:class:`django.forms.ModelMultipleChoiceField`).

    The :py:meth:`create_form` methods should be used to create new form
    instances.  A form created this way can be given an optional instance
    argument to allow for updating the instance. Any fields missing from data
    (but appearing in the :py:class:`form_class`'s :py:attr:`fields` attribute)
    will be copied over from the instance.
    """

    #: The form class. This should be a subclass of
    # :py:class:`django.forms.ModelForm`.
    form_class = None

    def create_form(self, data, request, instance=None, **kwargs):
        """Create a new form and pre-fill it with data.

        Args:
            data (dict):
                The request data to pass to the form.

            request (django.http.HttpRequest):
                The HTTP request.

            instance (django.db.models.Model):
                The instance model, if it exists. If this is not ``None``,
                fields that appear in the form class's ``fields`` attribute
                that do not appear in the ``data`` dict as keys will be copied
                from the instance.

            **kwargs (dict):
                Additional arguments. These will be passed to the resource's
                parser methods.

        Returns:
            django.forms.ModelForm: The form with data filled.
        """
        assert self.form_class, ('%s must define a form_class attribute.'
                                 % self.__class__.__name__)

        form = self.form_class(data=self._parse_form_data(data, request,
                                                          **kwargs),
                               instance=instance)

        if instance:
            missing_fields = [
                field_name for field_name in form.fields
                if field_name not in data
            ]

            form.data.update(model_to_dict(instance, missing_fields))

        return form

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
            dict: A mapping of field names to parsed values.
        """
        parsed_data = form_data.copy()

        for field, value in six.iteritems(form_data):
            parser = getattr(self, 'parse_%s_field' % field, None)

            if parser:
                parsed_data[field] = parser(value, request, **kwargs)
            else:
                parsed_data[field] = value

        return parsed_data
