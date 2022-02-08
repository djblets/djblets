"""Admin site definitions for extension models."""

from django.contrib import admin

from djblets.extensions.models import RegisteredExtension


class RegisteredExtensionAdmin(admin.ModelAdmin):
    list_display = ('class_name', 'name', 'enabled')


admin.site.register(RegisteredExtension, RegisteredExtensionAdmin)
