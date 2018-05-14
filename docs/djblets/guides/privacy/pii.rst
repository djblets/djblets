.. _privacy-pii:

================================================
Working with Personally Identifiable Information
================================================

Personally Identifiable Information, or :term:`PII`, is information that can
be used by itself or along with other information to point to or track an
individual person. For EU users protected by the :term:`GDPR`, this
information must be kept safe and can only be used with a valid legal
justification (such as :ref:`consent <privacy-consent>`).

Djblets provides utilities for safely working with PII.


.. _privacy-pii-safe-urls:

PII-Safe URLs
=============

:py:func:`~djblets.privacy.pii.build_pii_safe_page_url` generates a URL based
on the current page URL that redacts any PII that's found. It does this by
looking for certain keywords within both the URL pattern for the current URL
and the query string and, if found, redacting the values.

By default, this attempts to find any keywords containing ``user`` or ``mail``
anywhere in them, or any values containing a ``@`` character (which may be an
e-mail address).

When found, the value for that keyword is set to ``<REDACTED>``.

For example:

.. code-block:: python

   >>> from django.http import QueryDict
   >>> from djblets.privacy.pii import build_pii_safe_page_url
   >>>
   >>> build_pii_safe_page_url(
   ...     url='https://example.com/users/test-user/',
   ...     url_kwargs={
   ...         'username': 'test-user',
   ...     },
   ...     query_dict=QueryDict('email=test@example.com'))
   'https://example.com/users/<REDACTED>/?email=<REDACTED>'

Callers can pass a custom list of keywords through the ``unsafe_keywords=``
argument to :py:func:`~djblets.privacy.pii.build_pii_safe_page_url`, or set it
globally in :file:`settings.py`:

.. code-block:: python

   DJBLETS_PII_UNSAFE_URL_KEYWORDS = ['user', 'mail', 'uid']

If working with an :py:class:`~django.http.HttpRequest`, you can simplify this
by using :py:func:`~djblets.privacy.pii.build_pii_safe_page_url_for_request`:

.. code-block:: python

   from djblets.privacy.pii import build_pii_safe_page_url_for_request

   def my_view(request):
       url = build_pii_safe_page_url_for_request(request)
       ...

If you need a URL in a template, you don't need to compute it in the view. You
can use the :py:func:`{% pii_safe_page_url %}
<djblets.privacy.templatetags.djblets_privacy.pii_safe_page_url>` template
tag:

.. code-block:: html+django

   {% load djblets_privacy %}
   {% pii_safe_page_url %}
