"""A registry for configuration forms and pages."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.registries.errors import RegistrationError
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         ATTRIBUTE_REGISTERED, DEFAULT_ERRORS,
                                         OrderedRegistry, UNREGISTER)


# Errors for ConfigPageFormRegistry
CONFIG_PAGE_FORM_REGISTRY_DEFAULT_ERRORS = DEFAULT_ERRORS.copy()
CONFIG_PAGE_FORM_REGISTRY_DEFAULT_ERRORS.update({
    ALREADY_REGISTERED: _(
        'Could not register form %(item)r: This form is already '
        'registered.'
    ),
    ATTRIBUTE_REGISTERED: _(
        'Could not register form %(item)r: Another form (%(duplicate)r) '
        'is already registered with %(attr_name)s = %(attr_value)s.'
    ),
})


FORM_ALREADY_REGISTERED = 'form_already_registered'

# Errors for ConfigPageRegistry
CONFIG_PAGE_REGISTRY_DEFAULT_ERRORS = DEFAULT_ERRORS.copy()
CONFIG_PAGE_REGISTRY_DEFAULT_ERRORS.update({
    ALREADY_REGISTERED: _(
        'Could not register page %(item)s: This page is already registered.'
    ),
    ATTRIBUTE_REGISTERED: _(
        'Could not register page %(item)s: Another page (%(duplicate)s) '
        'is already registered with %(attr_name)s = %(attr_value)s.'
    ),
    FORM_ALREADY_REGISTERED: _(
        'Could not register page %(page)s: One of its forms (%(form)s) has '
        'already been registered with the %(duplicate)s page.',
    ),
    UNREGISTER: _(
        'Failed to unregister unknown account page %(item)s: This page is is '
        'not registered.'
    ),
})


class ConfigPageFormRegistry(OrderedRegistry):
    """A registry for managing configuration page forms."""

    lookup_attrs = ('form_id',)
    default_errors = CONFIG_PAGE_FORM_REGISTRY_DEFAULT_ERRORS


class ConfigPageRegistry(OrderedRegistry):
    """A registry for managing configuration pages.

    This allows subclasses to dynamically change which pages are available, as
    well as which forms are available on each page.

    The pages managed by this registry must subclass
    :py:class:`~djblets.configforms.mixins.DynamicConfigPageMixin`.
    """

    lookup_attrs = ('page_id',)
    default_errors = CONFIG_PAGE_REGISTRY_DEFAULT_ERRORS

    def __init__(self):
        super(ConfigPageRegistry, self).__init__()

        self._forms = ConfigPageFormRegistry()

        # Map form IDs to page IDs so that we can find pages that have already
        # registered forms when errors occur.
        self._form_to_page = {}

    def register(self, page_class):
        """Register a configuration page class.

        A page ID is considered unique and can only be registered once.

        This will also register all form classes on the page. If registration
        for any form fails, registration for the entire class will fail. In
        this case, the page will become unregistered, as well as any forms on
        that page that were successfully registered.

        Args:
            page_class (type):
                The page class to register, as a subclass of
                :py:class:`djblets.configforms.pages.ConfigPage`.

        Raises:
            djblets.registries.errors.AlreadyRegisteredError:
                Raised if the page has already been registered.

            djblets.registries.errors.RegistrationError:
                Raised if the page shares an attribute with an already
                registered page or if any of its forms share an attribute
                with an already registered form.
        """
        super(ConfigPageRegistry, self).register(page_class)

        # Set the form_classes to an empty list by default if it doesn't
        # explicitly provide its own, so that entries don't go into
        # DynamicConfigurationPageMixin's global list.
        if page_class.form_classes is None:
            page_class.form_classes = []

        # Set _default_form_classes when an account page class first registers.
        if page_class._default_form_classes is None:
            page_class._default_form_classes = list(page_class.form_classes)

        # If form_classes is empty, reload the list from _default_form_classes.
        if not page_class.form_classes:
            page_class.form_classes = list(page_class._default_form_classes)

        # We keep track of the pages that are successfully registered so that
        # if registration of any page fails, we can rollback those during
        # page unregistration.
        registered_forms = []

        for form_class in page_class.form_classes:
            try:
                self._forms.register(form_class)
                self._form_to_page[form_class.form_id] = page_class.page_id
            except RegistrationError:
                duplicate = self.get('page_id',
                                     self._form_to_page[form_class.form_id])

                self.unregister(page_class, registered_forms)
                raise RegistrationError(self.format_error(
                    FORM_ALREADY_REGISTERED,
                    page=page_class,
                    form=form_class,
                    duplicate=duplicate))

            registered_forms.append(form_class)

    def unregister(self, page_class, registered_forms=None):
        """Unregister a configuration page class.

        Args:
            page_class (type):
                The page class to unregister, as a subclass of
                :py:class:`djblets.configforms.pages.ConfigPage`.

            registered_forms (list, optional):
                The forms that have been successfully registered for the class.
                This attribute is only used when registration of forms was only
                partially successful.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised when the specified class or form is not registered.
        """
        super(ConfigPageRegistry, self).unregister(page_class)

        if registered_forms is None:
            # We copy the data so that we are not modifying the list while
            # iterating through it.
            registered_forms = list(page_class.form_classes)

        for form_class in registered_forms:
            self.remove_form_from_page(page_class, form_class)

    def add_form_to_page(self, page_class, form_class):
        """Add a form to the page.

        Callers should prefer to use
        :py:meth:`~djblets.configforms.mixins.DynamicConfigPageMixin.add_form`
        over this method.

        Args:
            page_class (type):
                The page to add the form to, as a subclass of
                :py:class:`djblets.configforms.pages.ConfigPage`.

            form_class (type):
                The form to add to the page, as a subclass of
                :py:class:`djblets.configforms.page.ConfigPage`.

        Raises:
            djblets.registries.errors.AlreadyRegisteredError:
                Raised if the form has already been registered.

            djblets.registries.errors.RegistrationError:
                Raised if the form shares an attribute with an already
                registered form.
        """
        self.populate()
        self._forms.register(form_class)
        page_class.form_classes.append(form_class)
        self._form_to_page[form_class.form_id] = page_class.page_id

    def remove_form_from_page(self, page_class, form_class):
        """Remove a form from the page.

        Callers should prefer to use
        :py:meth:`~djblets.configforms.mixins.DynamicConfigPageMixin.remove_form`
        over this method.

        Args:
            page_class (type):
                The page to remove the form from, as a subclass of
                :py:class:`djblets.configforms.pages.ConfigPage`.

            form_class (type):
                The form to remove from the page, as a subclass of
                :py:class:`djblets.configforms.forms.ConfigPageForm`.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised if the form was not previously registered.
        """
        self.populate()
        self._forms.unregister(form_class)
        page_class.form_classes.remove(form_class)
        del self._form_to_page[form_class.form_id]
