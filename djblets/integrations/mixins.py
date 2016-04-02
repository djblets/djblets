from __future__ import unicode_literals


class NeedsIntegrationManagerMixin(object):
    """Mixin for classes that require an integration manager to be defined.

    Some classes require access to an integration manager, which must be
    provided by the consuming application. This mixin provides
    :py:meth:`get_integration_manager` class method that, if not overridden,
    will raise a :py:exc:`NotImplementedError`.
    """

    @classmethod
    def get_integration_manager(cls):
        """Return the integration manager used for this class.

        Subclasses must override this to return an
        :py:class:`~djblets.integrations.manager.IntegrationManager` instance
        that will be used for any interaction management for this class.

        Returns:
            djblets.integrations.manager.IntegrationManager:
            The integration manager for this class.

        Raises:
            NotImplementedError:
                Raised if a subclass doesn't override this method.
        """
        raise NotImplementedError('%r must implement get_integration_manager()'
                                  % cls)
