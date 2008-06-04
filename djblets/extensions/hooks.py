from django.conf import settings
from django.core.urlresolvers import get_resolver

from djblets.extensions.base import ExtensionHook, ExtensionHookPoint


class URLHook(ExtensionHook):
    """
    A hook that installs custom URLs. These URLs reside in a project-specified
    parent URL.
    """
    __metaclass__ = ExtensionHookPoint

    def __init__(self, extension, patterns):
        ExtensionHook.__init__(self, extension)
        self.patterns = patterns

        # Install these patterns into the correct urlconf.
        if hasattr(settings, "EXTENSION_ROOT_URLCONF"):
            parent_urlconf = settings.EXTENSION_ROOT_URLCONF
        elif hasattr(settings, "SITE_ROOT_URLCONF"):
            parent_urlconf = settings.SITE_ROOT_URLCONF
        else:
            # Fall back on get_resolver's defaults.
            parent_urlconf = None

        self.parent_resolver = get_resolver(parent_urlconf)
        assert self.parent_resolver

        self.parent_resolver.url_patterns.extend(patterns)

    def shutdown(self):
        for pattern in self.patterns:
            self.parent_resolver.url_patterns.remove(pattern)
