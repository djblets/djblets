"""Compatibility module for management commands."""

from __future__ import unicode_literals

from optparse import OptionParser

from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.utils import six


class OptionParserWrapper(object):
    """Compatibility wrapper for OptionParser.

    This exports a more modern :py:class:`~argparse.ArgumentParser`-based API
    for :py:class:`~optparse.OptionParser`, for use when adding arguments in
    management commands. This only contains a subset of the functionality
    of :py:class:`~argparse.ArgumentParser`.
    """

    def __init__(self, parser):
        """Initialize the wrapper.

        Args:
            parser (optparse.OptionParser):
                The option parser.
        """
        self.parser = parser

    def add_argument(self, *args, **kwargs):
        """Add an argument to the parser.

        This is a simple wrapper that provides compatibility with most of
        :py:meth:`argparse.ArgumentParser.add_argument`. It supports the
        types that :py:meth:`optparse.OptionParser.add_option` supports (though
        those types should be passed as the primitive types and not as the
        string names).

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:meth:`optparse.OptionParser.add_option`.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`optparse.OptionParser.add_option`.
        """
        if not args[0].startswith('-'):
            # This is a positional argument, which is not supported by
            # optparse.
            return

        arg_type = kwargs.get('type')

        if arg_type is not None:
            kwargs['type'] = six.text_type(arg_type.__name__)

        self.parser.add_option(*args, **kwargs)


class BaseCommand(DjangoBaseCommand):
    """Base command compatible with a range of Django versions.

    This is a version of :py:class:`django.core.management.base.BaseCommand`
    that supports the modern way of adding arguments while retaining
    compatibility with older versions of Django. See the parent class's
    documentation for details on usage.
    """

    @property
    def use_argparse(self):
        return not bool(self.__class__.__dict__.get('option_list'))

    def create_parser(self, *args, **kwargs):
        # Start off by disabling add_arguments() from being invoked by the
        # parent. We want to call this ourselves.
        old_add_arguments = self.add_arguments
        self.add_arguments = lambda *args: None

        parser = super(BaseCommand, self).create_parser(*args, **kwargs)

        self.add_arguments = old_add_arguments

        # Now invoke add_arguments() ourselves, using a wrapper for older
        # versions of Django.
        if isinstance(parser, OptionParser):
            self.add_arguments(OptionParserWrapper(parser))
        else:
            self.add_arguments(parser)

        return parser

    def add_arguments(self, parser):
        # This is intentionally meant to be blank by default.
        pass

    def __getattribute__(self, name):
        """Return an attribute from the command.

        If the attribute name is "option_list", some special work will be
        done to ensure we're returning a valid list that the caller can work
        with, even if the options were created in :py:meth:`add_arguments`.

        Args:
            name (unicode):
                The attribute name.

        Returns:
            object:
            The attribute value.
        """
        if (name == 'option_list' and
            not getattr(self, '_use_real_option_list', False)):
            # The parser is going to turn around and fetch self.option_list
            # (which will contain the defaults for the class, or the options
            # defined by the subclass if it hasn't been updated yet). We need
            # to make sure it gets the real copy.
            self._use_real_option_list = True
            parser = self.create_parser('', self.__class__.__module__)
            self._use_real_option_list = False

            assert isinstance(parser, OptionParser)

            # We're going to get more than the options defined for the
            # command. We'll also get the built-in --help and --version
            # options, which are special and will break call_command(), as
            # they don't have a destination variable and aren't listed in the
            # command's option_list normally. So filter those out.
            return [
                option
                for option in parser.option_list
                if option.get_opt_string() not in ('--help', '--version')
            ]

        return super(BaseCommand, self).__getattribute__(name)
