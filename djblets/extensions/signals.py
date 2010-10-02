import django.dispatch


extension_initialized = django.dispatch.Signal(providing_args=["ext_class"])
extension_uninitialized = django.dispatch.Signal(providing_args=["ext_class"])
