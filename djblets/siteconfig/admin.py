"""Administration UI registrations for site configurations."""

from __future__ import unicode_literals

from django.contrib import admin

from djblets.siteconfig.models import SiteConfiguration


class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site', 'version')


admin.site.register(SiteConfiguration, SiteConfigurationAdmin)
