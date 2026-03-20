.. _ratelimit-guide:

========================
Rate Limiting Operations
========================

.. versionadded:: 5.3

Djblets provides a generic, reusable mechanism for rate limiting any
operation in your application, helping services fail gracefully when
overloaded.

This is useful for rate-limiting:

* Expensive downloads or calculations
* SMS-based two-factor auth setup
* AI requests
* Form submissions
* Authentication and API requests (see :py:mod:`djblets.auth.ratelimit` for
  a pre-built implementation)

:py:mod:`djblets.protect.ratelimit` lets you configure rate limit durations
and to check or perform a hit against a rate limit.


General Usage
=============

It's up to the consumer to decide what will be rate limited and how.

Rate limits are represented by
:py:class:`~djblets.protect.ratelimit.RateLimit` objects. These define how
many hits are allowed in a given time period, and are passed to other rate
limit functions.

Rate limits are checked against keys using
:py:func:`~djblets.protect.ratelimit.check_rate_limit`. These are strings (or,
preferably, lists of strings) that identify the resource and entity being rate
limited. They might include a username, IP address, or some other identifier.

The result of a check is a
:py:class:`~djblets.protect.ratelimit.RateLimitUsage` object representing the
number of hits against the key, the total number allowed, the time remaining
until the limit resets, and whether the limit has been hit.


Defining a RateLimit
====================

There are two ways to construct a
:py:class:`~djblets.protect.ratelimit.RateLimit`:

1. Passing a rate limit string to :py:meth:`RateLimit.parse()
   <djblets.protect.ratelimit.RateLimit.parse>`.

   This allows you to express the rate limit in terms of seconds, minutes,
   hours, or days. This takes the following forms:

   * ``X/Ys`` -- X hits in Y seconds
   * ``X/Ym`` -- X hits in Y minutes
   * ``X/Yh`` -- X hits in Y hours
   * ``X/Yd`` -- X hits in Y days

   ``Y`` can be omitted if specifying just 1.

2. Passing the hit limit and the period in seconds as arguments to the
   constructor.

   This is ideal if you already have the time period available in seconds,
   or want a period that isn't expressed well through a rate limit string.


Some examples:

.. code-block:: python

   from djblets.protect.ratelimit import RateLimit


   # Define a rate limit of 100 lasting 30 minutes:
   rate_limit = RateLimit(
       period_secs=30 * 60,
       total_limit=100,
   )

   # 10 in 30 seconds.
   rate_limit = RateLimit.parse('10/30s')

   # 200 in 15 minutes.
   rate_limit = RateLimit.parse('200/15m')

   # 250 in 3 hours.
   rate_limit = RateLimit.parse('250/3h')

   # 1000 in 1 day.
   rate_limit = RateLimit.parse('1000/d')


Choosing a Rate Limit Key
=========================

When choosing a rate limit key, you'll want to associate any information on
both the resource and the entity being rate limited.

A rate limit key can be a string or a list of strings. You'll usually want
to use lists, which will safely escape any dynamic content that make up the
key (such as usernames).

Some examples include:

* ``['reset-password', email]``
* ``['api-request', username_or_ip]``
* ``['sms-setup', phone_number, username_or_ip]``

When designing a key, follow these basic guidelines:

1. **Namespace your keys**

   This will help avoid collisions. You can provide as many levels for
   the namespace as appropriate. The namespace should be placed at the
   start of the key, from most-general to most-specific category.

2. **Use stable keys**

   Make sure the key for any given prefix always has the same number of
   elements so you don't risk any unexpected collisions when using dynamic
   variables like usernames.

3. **Be specific with your keys**

   Don't make a key more broad or more fine-grained than it should be.
   Consider what exactly should be rate limited and what users or other
   targets should be considered.

.. tip::

   Often, rate limits will be tied to a username or, if not logged in, an IP
   address.

   For this case, you may :py:func:`djblets.auth.ratelimit.get_user_id_or_ip`,
   which takes a :py:class:`~django.http.HttpRequest` and returns the user
   ID or IP address as appropriate.


Checking a Rate Limit and Incrementing
======================================

To check a rate limit, call
:py:func:`~djblets.protect.ratelimit.check_rate_limit`, passing in the
rate limit, key, and ``increment_count=True``. This will increment the count
towards the limit and return the results.

.. code-block:: python

   from djblets.auth.ratelimit import get_user_id_or_ip
   from djblets.protect.ratelimit import RateLimit, check_rate_limit


   rate_limit = RateLimit.parse('10/h')
   username_or_ip = get_user_id_or_ip(request)

   # This will count toward the limit.
   result = check_rate_limit(
       rate_limit=rate_limit,
       key=['api-request', username_or_ip],
       increment_count=True,
   )

The resulting :py:class:`~djblets.protect.ratelimit.RateLimitUsage` will
contain the details of that hit. The attributes include:

``count``:
   The number of hits against the rate limit key.

``is_limited``:
   Whether the limit has been exceeded.

``limit``:
   The total number of attempts allowed for the rate limit.

``time_left_secs``:
   The time remaining in seconds before the rate limit is reset for the key.

The consumer is responsible for enforcing any rate limiting behavior based
on the result.

.. tip::

   As a convenience, you can pass a rate limit string instead of a
   :py:class:`~djblets.protect.ratelimit.RateLimit` object:

   .. code-block:: python

      result = check_rate_limit(
          rate_limit='10/h',
          key=['api-request', username_or_ip],
          increment_count=True,
      )


Passively Checking
==================

To passively check the number of hits remaining against a rate limit,
call :py:func:`~djblets.protect.ratelimit.check_rate_limit` with just the
rate limit and key. This will return a
:py:class:`~djblets.protect.ratelimit.RateLimitUsage` as above, but won't
count toward the limit.

For example:

.. code-block:: python

   from djblets.auth.ratelimit import get_user_id_or_ip
   from djblets.protect.ratelimit import RateLimit, check_rate_limit


   rate_limit = RateLimit.parse('10/h')
   username_or_ip = get_user_id_or_ip(request)

   # This won't count toward the limit.
   result = check_rate_limit(
       rate_limit=rate_limit,
       key=['api-request', username_or_ip],
   )
