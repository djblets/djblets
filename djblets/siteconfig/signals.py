from __future__ import unicode_literals

from django.dispatch import Signal


#: Emitted when a SiteConfiguration has loaded.
#:
#: This can be used by callers that depend on
#: :py:class:`~djblets.siteconfig.models.SiteConfiguration` to handle reloading
#: or recomputing data from settings that may have changed in another process
#: or server.
#:
#: Args:
#:     siteconfig (djblets.siteconfig.models.SiteConfiguration)
#:         The site configuration that has been loaded.
#:
#:     old_siteconfig (djblets.siteconfig.models.SiteConfiguration)
#:         The old site configuration. The caller can compare the settings
#:         between the new one and this one to see if it needs to handle
#:         anything.
siteconfig_reloaded = Signal(providing_args=['siteconfig', 'old_siteconfig'])
