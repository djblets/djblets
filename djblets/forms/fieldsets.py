"""Utilities related to django.contrib.admin fieldsets."""

from __future__ import unicode_literals


def filter_fieldsets(form, admin=None, fieldsets=None, exclude=None,
                     exclude_collapsed=True):
    """Filter fieldsets.

    This method allows us to filter fieldsets from a ModelAdmin to exclude
    fields (or an entire fieldset).

    Args:
        form (type or django.forms.Form):
            The form (or form class) to retrieve fieldsets for.

        admin (django.contrib.admin.ModelAdmin, optional):
            The model admin to retrieve fieldsets from. If this argument is not
            provided, ``fieldsets`` will be used instead.

        fieldsets (tuple, optional):
            The fieldsets to use.

        exclude (list of unicode, optional):
            An optional list of fields to exclude.

        exclude_collapsed (bool, optional):
            Whether or not to exclude fieldsets marked as collapsed by default.

    Yields:
        dict:
        An entry for each field set that should be rendered.

        If a field set would have no rendered fields, it is not yielded.
    """
    if admin is None and fieldsets is None:
        raise ValueError(
            'filter_fieldsets: either admin or fieldsets must be provided.'
        )

    if exclude is None:
        exclude = []

    exclude.extend(list(form._meta.exclude or []))

    if fieldsets is None:
        assert hasattr(admin, 'fieldsets'), 'admin.fieldsets is undefined.'
        assert iter(admin.fieldsets), 'admin.fieldsets should be iterable.'
        fieldsets = admin.fieldsets

    for name, data in fieldsets:
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
