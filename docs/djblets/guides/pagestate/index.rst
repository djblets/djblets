.. _pagestate-guide:

=======================
Dynamic Page Injections
=======================

Extensible products often need to add content to a page, such as ``<script>``
tags, CSS, notice banners, and navigation items. This needs to be factored
into a page's ETags so that older content doesn't get stuck in a browser
cache somewhere.

The :py:mod:`djblets.pagestate` module makes this easy by offering the
following:

* Template-defined points where data can be injected.

* A method for manually adding content to a template point.

* Injector classes that let calls dynamically generate content for any
  template points.

We'll walk through how this works.


Setting Up
==========

You'll first need to enable the template tag library and middleware. Add
the following to your project's :file:`settings.py`:

.. code-block:: python

   INSTALLED_APPS
       ...,
       'djblets.pagestate',
       ...
   ]

   MIDDLEWARE = [
       ...
       'djblets.pagestate.middleware.PageStateMiddleware',
       ...
   ]


Making a Template Dynamic
=========================

To make a portion of your template dynamic, simply use the
:py:func:`{% page_hook_point %} <djblets.pagestate.templatetags.
djblets_pagestate.page_hook_point>` template tag from the
:py:mod:`djblets.pagestate.templatetags.djblets_pagestate` template library,
and give it a name.

For example:

.. code-block:: html+django

   {% load djblets_pagestate %}

   <html>
    <head>
     <title>Page Title</title>
     {% page_hook_point "scripts" %}
    </head>
    <body>
     ...
     {% page_hook_point "after-content" %}
    </body>
   </html>


This defines two points:

1. ``scripts``
2. ``after-content``

Both of these will be replaced with content injected either manually or
from registered injectors.


Manually Injecting Content
==========================

During your request/response cycle, you can manually inject content into
a template hook point.

To do this:

1. Fetch the :py:class:`~djblets.pagestate.state.PageState` for the
   :py:class:`~django.http.HttpRequest`, using
   :py:meth:`PageState.for_request(request)
   <djblets.pagestate.pagestate.PageState.for_request>`.

2. Call :py:meth:`PageState.inject() <djblets.pagestate.pagestate.PageState.
   inject>` with the content and optional ETag to inject.

For example:

.. code-block:: python

   from django.http import HttpRequest, HttpResponse
   from django.shortcuts import render
   from django.utils.html import mark_safe
   from djblets.pagestate.state import PageState

   def my_view(
       request: HttpRquest,
   ) -> HttpResponse:
       page_state = PageState.for_request(request)

       page_state.inject('scripts', {
           'content': mark_safe('<script>alert("hi!")</script>'),
       })

       page_state.inject('after-content', {
           'content': build_some_content_html(),
           'etag': build_some_content_etag(),
       });

       return render(request, 'base.html')


These will be placed in their respective template hook points.


Building Dynamic Injectors
==========================

You don't have to manually inject content in every view. If you have content
that's going to be common across pages, you can create an injector.

Injectors are classes that adhere to :py:class:`~djblets.pagestate.
injectors.PageStateInjectorProtocol`. They register a unique
:py:attr:`injector_id <djblets.pagestate.injectors.PageStateInjectorProtocol.
injector_id>` and implement :py:class:`iter_page_state_data()
<djblets.pagestate.injectors.PageStateInjectorProtocol.iter_page_state_data>`.

They're then registered in the :py:attr:`djblets.pagestate.injectors.
page_state_injectors`.

For example:

.. code-block:: python

   from collections.abc import Iterator

   from django.http import HttpRequest
   from django.template import Context
   from django.utils.html import format_html
   from djblets.pagestate.injectors import page_state_injectors
   from djblets.pagestate.state import PageStateData


   class MyInjector:
       injector_id = 'my-injector'

       def iter_page_state_data(
           self,
           *,
           point_name: str,
           request: HttpRequest,
           context: Context,
       ) -> Iterator[PageStateData]
           if point_name == 'scripts':
               for i in range(10):
                   yield {
                       'content': format_html(
                           '<script>console.log("i = {}");</script>',
                           i),
                       'etag': str(i),
                   }

   page_state_injectors.register(MyInjector())


This simple injector will add a series of ``console.log()`` statements
for the ``scripts`` template hook point, generating them dynamically based
on a range of numbers.

In practice, you might use an injector to look up data from a database, a
:ref:`registry <writing-registries>`, or another source.


Cache-Busting with ETags
========================

When injecting, it's recommended to provide an ETag that differentiates that
particular piece of content from another that it might generate.

In the above example, we're just using the string version of the number in
the loop, which is safe if that's the only part of the HTML that would
change. You might want to include more information than that, such as a
version identifier for the format of the HTML.

If an ETag isn't specified, the full content will be used for part of the
ETag.

*If* the resulting HTTP response includes an ETag, then the ETag data
injected into the page state will be mixed into it, forming a new ETag.
This ensures that the ETag always changes to reflect any injections.

If the HTTP response does not include an ETag, the ETag data will *not*
be included, in order to avoid unintentionally caching the full page (which
may be dynamic in other ways).
