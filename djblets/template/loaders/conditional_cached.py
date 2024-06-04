from django.conf import settings
from django.template.loaders import cached


class Loader(cached.Loader):
    """Caches template loading results only if not in developer mode.

    This extends Django's built-in 'cached' template loader to only
    perform caching if ``settings.PRODUCTION`` is False. That helps to keep
    the site nice and speedy when in production, without causing headaches
    during development.
    """
    def load_template(self, *args, **kwargs):
        if not getattr(settings, 'PRODUCTION', not settings.DEBUG):
            self.reset()

        return super(Loader, self).load_template(*args, **kwargs)
