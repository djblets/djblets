#
# djblets_forms.py -- Form-related template tags
#
# Copyright (c) 2008-2009  Christian Hammond
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

from __future__ import unicode_literals

from django import forms, template
from django.utils.html import conditional_escape, format_html


register = template.Library()


@register.simple_tag
def label_tag(field):
    """Render the tag for a field's label.

    This generates labels similar to the administration UI's own field labels,
    providing styling for required fields and checkboxes.

    If the label is explicitly set to an empty string on the field, no label
    will be rendered, matching Django's default behavior.

    Args:
        field (django.forms.BoundField):
            The bound field on the form to render the label for.

    Returns:
        django.utils.safestring.SafeText:
        The resulting HTML for the label.

    Example:
        .. code-block:: html+django

           {% label_for form.my_field %}
    """
    if not field.label:
        return ''

    is_checkbox = is_field_checkbox(field)

    # Build the list of CSS classes to apply to the label.
    classes = []

    if field.field.required:
        classes.append('required')

    if is_checkbox:
        classes.append('vCheckboxLabel')

    if classes:
        classes_html = format_html(' class="{0}"', ' '.join(classes))
    else:
        classes_html = ''

    # Build the text for the label.
    label = field.label

    if not is_checkbox:
        label += ':'

    # Render the result.
    return format_html('<label for="{0}"{1}>{2}</label>',
                       form_field_id(field),
                       classes_html,
                       label)


@register.filter
def form_field_id(field):
    """Render the ID of a field.

    This will derive the field's ID in the form and output it, for use in
    utility functions or custom HTML.

    Args:
        field (django.forms.BoundField):
            The bound field on the form.

    Returns:
        django.utils.safestring.SafeText:
        The resulting ID as safe HTML.

    Example:
        .. code-block:: html+django

           <span data-field-id="{{form.my_field|form_field_id}}"></span>
    """
    widget = field.field.widget
    field_id = widget.attrs.get('id') or field.auto_id or ''

    if field_id:
        field_id = widget.id_for_label(field_id)

    return conditional_escape(field_id)


@register.filter
def is_field_checkbox(field):
    """Return whether or not this field is effectively a checkbox field.

    A field is considered to be a checkbox field if its widget is a
    :py:class:`~django.forms.CheckboxInput`.

    Args:
        field (django.forms.BoundField):
            The bound field on the form.

    Returns:
        bool:
        ``True`` if this is a checkbox field. ``False`` if not.

    Example:
        .. code-block:: html+django

           {% if field|is_field_checkbox %}
           ...
           {% endif %}
    """
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_checkbox_row(field):
    """Return whether the field's row is a checkbox-ish row.

    This will return ``True`` if rendering a checkbox, radio button, or
    multi-select checkbox.

    Args:
        field (django.forms.BoundField):
            The bound field on the form.

    Returns:
        bool:
        ``True`` if this is a checkbox-ish field. ``False`` if not.

    Example:
        .. code-block:: html+django

           {% if field|is_checkbox_row %}
           ...
           {% endif %}
    """
    return isinstance(field.field.widget, (forms.CheckboxInput,
                                           forms.RadioSelect,
                                           forms.CheckboxSelectMultiple))


@register.filter
def form_field_has_label_first(field):
    """Return whether a form label should be displayed before the widget.

    This helps when rendering labels and widgets in the correct order.
    Typically, non-checkbox widgets are preceded by a label, and this lets
    templates determine if that should be the case for a given field.

    Args:
        field (django.forms.BoundField):
            The bound field on the form.

    Returns:
        bool:
        ``True`` if the label should appear before the widget.
        ``False`` if the widget should appear before the label.

    Example:
        .. code-block:: html+django

           {% if field|form_field_has_label_first %}
           ...
           {% endif %}
    """
    return not is_field_checkbox(field)


@register.filter
def get_fieldsets(form):
    """Normalize and iterate over fieldsets in a form.

    This will loop through the fieldsets on a given form, converting either
    standard Django style or legay Djblets style fieldset data into a standard
    form and returning it to the template.

    Args:
        form (django.forms.Form):
            The form containing the fieldsets.

    Yields:
        tuple:
        A tuple of (fieldset_title, fieldset_info).

    Example:
        .. code-block:: html+django

           {% for fieldset_title, fieldset in form|get_fieldsets %}
           ...
           {% endfor %}
    """
    try:
        fieldsets = form.Meta.fieldsets
    except AttributeError:
        fieldsets = []

    for fieldset in fieldsets:
        if isinstance(fieldset, tuple):
            # This is a standard Django-style fieldset entry. It's a tuple
            # of (title, info).
            yield fieldset
        elif isinstance(fieldset, dict):
            # This is a legacy Djblets-style fieldset entry. It's a dictionary
            # that may contain the title as a "title" key.
            yield fieldset.get('title'), fieldset
        else:
            raise ValueError('Invalid fieldset value: %r' % fieldset)
