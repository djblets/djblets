.. privacy-services-guides:

====================
Service Integrations
====================

Djblets provides helpful templates for common service integrations that
default to the highest privacy settings available.


Google Analytics
================

The ``privacy/services/google_analytics.html`` template enables use of
`Google Analytics`_, enabling anonymized IPs and :term:`PII`-safe page titles
and URLs.

Usage requires the following settings in :file:`settings.py`:

.. code-block:: python

   GOOGLE_ANALYTICS_ENABLED = True
   GOOGLE_ANALYTICS_TRACKING_CODE = 'UA-12345678-9'


And then including the template file:

.. code-block:: html+django

   {% include "privacy/services/google_analytics.html" %}


By default, this will send the current page title and a best-attempt at a URL
redacting any PII (see :ref:`privacy-pii-safe-urls`).

Views can also provide PII-safe page titles by passing a ``pii_safe_title``
in the context for the template. This will be sent to Google Analytics instead
of the real page title, keeping private data safe. We recommend this for any
pages containing a username, full name, or e-mail address.


.. _Google Analytics: https://analytics.google.com/
