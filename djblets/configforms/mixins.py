"""Utility mixins for configuration forms."""

from __future__ import unicode_literals


class DynamicConfigPageMixin(object):
    """A mixin for utilizing a registry to keep track of the pages and forms.

    Objects using this mixin can have a dynamic list of forms, which can be
    updated by callers. New forms can be registered on them and existing forms
    can be removed. With this mixin, it is possible to extend a configuration
    page, allowing each form to load, validate, and save without the page
    hard-coding support for each form.

    Forms utilizing this mixin are required to set the :py:attr:`registry`
    attribute to an instance of
    :py:class:`~djblets.configforms.registry.ConfigPageRegistry`.

    To manage the forms on a page, the :py:meth:`add_form` and
    :py:meth:`remove_form` methods should be used.
    """

    #: The registry to use.
    #:
    #: This should be an instance of
    # :py:class:`~djblets.configforms.registry.ConfigPageRegistry`.
    registry = None

    _default_form_classes = None

    @classmethod
    def add_form(cls, form_class):
        """Add a form to the page.

        Args:
            form_class (type):
                The form to add to the page, as a subclass of
                :py:class:`~djblets.configforms.page.ConfigPage`.
        """
        cls.registry.add_form_to_page(cls, form_class)

    @classmethod
    def remove_form(cls, form_class):
        """Remove a form from the page.

        Args:
            form_class (type):
                The form to remove from the page, as a subclass of
                :py:class:`~djblets.configforms.forms.ConfigPageForm`.
        """
        cls.registry.remove_form_from_page(cls, form_class)
