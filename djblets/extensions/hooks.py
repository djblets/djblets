from djblets.extensions.base import ExtensionHook, ExtensionHookPoint


class URLHook(ExtensionHook):
    __metaclass__ = ExtensionHookPoint

    def __init__(self, extension, patterns):
        ExtensionHook.__init__(self, extension)
        self.patterns = patterns
