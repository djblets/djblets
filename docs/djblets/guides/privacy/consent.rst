.. _privacy-consent:

============================
Getting and Checking Consent
============================

.. py:currentmodule:: djblets.privacy.consent

If your application passes a user's personal information (such as :term:`PII`)
to third-party services, it's often good to get the user's consent (and for EU
users protected by the :term:`GDPR`, it may be legally required). This consent
may be needed for two features, or for a dozen, and if you're making use of
extensions, there may be even more things that need consent.

Djblets provides a :py:mod:`djblets.privacy.consent` module for registering
things that require consent, for checking on whether consent was given, for
providing UI for consent management, and for auditing the consent choices made
by the user over time in a safe and secure way.


Consent Requirements
====================

:py:class:`~.base.ConsentRequirement` is the main class that everything else
centers around. It defines a requirement with a unique ID and information
about what requires consent, primarily for display purposes.

Any part of a codebase requiring consent will construct an instance of this
class (or a subclass of it) and register it in the
:py:class:`~.registry.ConsentRequirementsRegistry` (accessible through
:py:func:`~.registry.get_consent_requirements_registry`.

This looks like:

.. code-block:: python

   from djblets.privacy.consent import (ConsentRequirement,
                                        get_consent_requirements_registry)


   my_requirement = ConsentRequirement(
       requirement_id='my-requirement-id',
       name='My Requirement',
       intent_description='A description about the requirement, presented '
                          'to the user clearly and informatively.',
       data_use_description='A brief summary of what data gets sent to the '
                            'data processor service.',
       learn_more_url='https://example.com/privacy#my-requirement',
       icons={
           '1x': '/path/to/logo.png',
           '2x': '/path/to/logo@2x.png',
       })

   get_consent_requirements_registry().register(my_requirement)

These requirements can be checked for consent to determine if consent was
granted, denied, or not yet decided upon:

.. code-block:: python

   from djblets.privacy.consent import Consent

   ...

   consent = my_requirement.get_consent(user)

   if consent == Consent.GRANTED:
       ...
   elif consent == Consent.DENIED:
       ...
   elif consent == Consent.UNSET:
       ...


Tracking Consent Decisions
==========================

A decision made on a consent requirement is represented as a
:py:class:`~.base.ConsentData` instance, tracked by a
:py:class:`~.tracker.BaseConsentTracker`.

:py:class:`~.base.ConsentData` stores whether a given
:py:class:`~.base.ConsentRequirement` ID has been
granted or denied, along with additional data for audit purposes: The consent
decision's timestamp, source location (which can be a URL or some other
identifier), and custom application-provided metadata.

The consent tracker (accessible via
:py:func:`~.tracker.get_consent_tracker`) tracks that
consent, recording it for later audits. It stores the data along with an
identifier that maps to the user (defaults to a SHA256 hash of their e-mail
address).

The default consent tracker uses the database (storing in the
:py:class:`~djblets.privacy.models.StoredConsentData` model), but applications
can change how consent is stored and looked up by subclassing the base
tracker and setting ``settings.DJBLETS_PRIVACY_CONSENT_TRACKER`` to its full
module/class path.

If using the built-in UI, much of this happens behind the scenes. If you need
to record consent directly, you can use
:py:meth:`~.tracker.BaseConsentTracker.record_consent_data_list`.

.. code-block:: python

   from django.utils import timezone
   from djblets.privacy.consent import get_consent_tracker

   ...

   now = timezone.now()

   get_consent_tracker().record_consent_data_list(
       user,
       [
           my_requirement_1.build_consent_data(
               granted=True,
               timestamp=now,
               source='https://example.com/accounts/consent/'),
           my_requirement_2.build_consent_data(
               granted=False,
               timestamp=now,
               source='https://example.com/accounts/consent/'),
       ])

Or to get all the consent decisions filed by a user (for display in the UI,
for example), use :py:meth:`~.tracker.BaseConsentTracker.get_all_consent`.

.. code-block:: python

   from django.utils import six, timezone
   from djblets.privacy.consent import get_consent_tracker

   ...

   now = timezone.now()

   all_consent = get_consent_tracker().get_all_consent(user)

   if my_requirement_1.requirement_id in all_consent:
       if my_requirement_1.requirement_id] == Consent.GRANTED:
          ...
       elif my_requirement_1.requirement_id] == Consent.DENIED:
          ...
