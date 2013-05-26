#
# hooks.py -- Common extension hook points.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from django.core.urlresolvers import NoReverseMatch, reverse
from django.template.loader import render_to_string

from djblets.extensions.base import ExtensionHook, ExtensionHookPoint


class URLHook(ExtensionHook):
    """Custom URL hook.

    A hook that installs custom URLs. These URLs reside in a project-specified
    parent URL.
    """
    __metaclass__ = ExtensionHookPoint

    def __init__(self, extension, patterns):
        super(URLHook, self).__init__(extension)
        self.patterns = patterns
        self.dynamic_urls = self.extension.extension_manager.dynamic_urls
        self.dynamic_urls.add_patterns(patterns)

    def shutdown(self):
        super(URLHook, self).shutdown()

        self.dynamic_urls.remove_patterns(self.patterns)


class TemplateHook(ExtensionHook):
    """Custom templates hook.

    A hook that renders a template at hook points defined in another template.
    """
    __metaclass__ = ExtensionHookPoint

    _by_name = {}

    def __init__(self, extension, name, template_name=None, apply_to=[]):
        super(TemplateHook, self).__init__(extension)
        self.name = name
        self.template_name = template_name
        self.apply_to = apply_to

        if not name in self.__class__._by_name:
            self.__class__._by_name[name] = [self]
        else:
            self.__class__._by_name[name].append(self)

    def shutdown(self):
        super(TemplateHook, self).shutdown()

        self.__class__._by_name[self.name].remove(self)

    def render_to_string(self, request, context):
        """Renders the content for the hook.

        By default, this renders the provided template name to a string
        and returns it.
        """
        return render_to_string(self.template_name, context)

    def applies_to(self, context):
        """Returns whether or not this TemplateHook should be applied given the
        current context.
        """

        # If apply_to is empty, this means we apply to all - so
        # return true
        if not self.apply_to:
            return True

        # Extensions Middleware stashes the kwargs into the context
        kwargs = context['request']._djblets_extensions_kwargs
        current_url = context['request'].path_info

        # For each URL name in apply_to, check to see if the reverse
        # URL matches the current URL.
        for applicable in self.apply_to:
            try:
                reverse_url = reverse(applicable, args=(), kwargs=kwargs)
            except NoReverseMatch:
                # It's possible that the URL we're reversing doesn't take
                # any arguments.
                try:
                    reverse_url = reverse(applicable)
                except NoReverseMatch:
                    # No matches here, move along.
                    continue

            # If we got here, we found a reversal.  Let's compare to the
            # current URL
            if reverse_url == current_url:
                return True

        return False

    @classmethod
    def by_name(cls, name):
        return cls._by_name.get(name, [])
