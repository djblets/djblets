"""Utilities related to :py:mod:`django.contrib.admin` fieldsets."""

from __future__ import unicode_literals


def filter_fieldsets(admin, form, exclude=None, exclude_collapsed=True):
    """Filter fieldsets.

    Django :py:class:`~django.contrib.admin.ModelAdmin` classes can define a
    set of fieldsets, but not in a way that is generically useful on their own
    outside of the admin site. This function yields field set information in a
    more usable fashion.

    Args:
        admin (django.contrib.admin.ModelAdmin):
            The model admin to retrieve fieldsets from.

        form (django.forms.Form):
            The form to retrieve fieldsets for.

        exclude (list of unicode, optional):
            An optional list of fields to exclude.

        exclude_collapsed (bool, optional):
            Whether or not to exclude fieldsets marked as collapsed by default.

    Yields:
        dict:
        An entry for each field set that should be rendered.

        If a field set would have no rendered fields, it is not yielded.
    """
    if exclude is None:
        exclude = []

    exclude.extend(list(form._meta.exclude or []))

    for name, data in admin.fieldsets:
        fieldset = data.copy()

        if exclude_collapsed and 'collapse' in data.get('classes', ()):
            continue

        fieldset['fields'] = [
            field_name
            for field_name in data['fields']
            if field_name not in exclude
        ]

        if fieldset['fields']:
            yield (name, fieldset)
