from django import template


register = template.Library()


@register.simple_tag
def my_extension_template_tag():
    return 'Hello, world!'
