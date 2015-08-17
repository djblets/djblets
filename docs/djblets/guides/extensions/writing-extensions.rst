.. _writing-extensions:

==================
Writing Extensions
==================

.. currentmodule:: djblets.extensions.extension


Overview
--------

Extensions are a way to enhance a program's feature set through pluggable
third-party modules. This works much like browser extensions, but for your own
program.

This guide will go over some of the basics of an extension, to help you write
your own.


Extension Subclasses
--------------------

All extensions must be subclasses of :py:class:`Extension`. Note that the
application you're writing an extension for may have their own class you must
subclass instead (for example, Review Board uses
:py:class:`reviewboard.extensions.base.Extension`), so consult their
documentation.


Configuration
-------------

If an extension supports configuration in the UI, it should set
:py:attr:`Extension.is_configurable` to ``True``.

If an extension would like to specify defaults for the settings dictionary it
should provide a dictionary in :py:attr:`Extension.default_settings`.

If an extension would like a django admin site for modifying the database,
it should set :py:attr:`Extension.has_admin_site` to ``True``.


Static Media
------------

Extensions should list all other extension names that they require in
:py:attr:`Extension.requirements`.

Extensions can define static media bundle for Less/CSS and JavaScript files,
which will automatically be compiled, minified, combined, and packaged. An
Extension class can define :py:attr:`Extension.css_bundles` and
:py:attr:`Extension.js_bundles`. Each is a dictionary mapping bundle names to
bundle dictionary. These mostly follow the Django Pipeline bundle format.

For example:

.. code-block:: python

   class MyExtension(Extension):
       css_bundles = {
           'default': {
               'source_filenames': ['css/default.css'],
               'output_filename': 'css/default.min.css',
           },
       }

``source_filenames`` is a list of files within the extension module's static/
directory that should be bundled together. When testing against a developer
install with ``DEBUG = True``, these files will be individually loaded on the
page. However, in a production install, with a properly installed extension
package, the compiled bundle file will be loaded instead, offering a file size
and download savings.

``output_filename`` is optional. If not specified, the bundle name will be
used as a base for the filename.

A bundle name of ``default`` is special. It will be loaded automatically
on any page supporting extensions (provided the ``load_extensions_js`` and
``load_extensions_css`` template tags are used).

Bundles can also specify an optional ``apply_to`` field, which is a list
of URL names for pages that the bundle should be automatically loaded on.
This works like the ``default`` bundle, but for those specific pages.

Bundles can also be loaded manually within a
:py:class:`~djblets.extensions.hooks.TemplateHook` template
by using ``{% ext_css_bundle extension "bundle-name" %}`` or
``{% ext_js_bundle extension "bundle-name" %}``.


JavaScript extensions
---------------------

An Extension subclass can define one or more JavaScript extension classes,
which may apply across all pages or only a subset of them.

Each is defined as a :py:class:`JSExtension` subclass, and listed in
Extension's :py:attr:`Extension.js_extensions` list. See the documentation on
JSExtension for more information.

Any page using the ``init_js_extensions`` template tag will automatically
initialize any JavaScript extensions appropriate for that page, passing the
server-stored settings.


Middleware
----------

If an extension has any middleware, it should set
:py:attr:`Extension.middleware` to a list of class names. This extension's
middleware will be loaded after any middleware belonging to any extensions in
the :py:attr:`Extension.requirements` list.


Template Context Processors
---------------------------

Extensions may need to provide additional context variables to templates.
This can usually be accomplished through a
:py:class:`~djblets.extensions.hooks.TemplateHook`, but sometimes it's
necessary to provide context variables for other pages (such as those
controlled by a third-party module).

To add additional context processors, set
:py:attr:`Extension.context_processors` to a list of class names. They will be
added to ``settings.TEMPLATE_CONTEXT_PROCESSORS`` automatically.
