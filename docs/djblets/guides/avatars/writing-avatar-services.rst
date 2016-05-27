.. _writing_avatar_services:

=======================
Writing Avatar Services
=======================

.. currentmodule:: djblets.avatars.services


Overview
--------

Avatar services provide your application with customizable ways for users to
pick an avatar. Avatar services also cache the result of lookup for each
user and size requested on the current :py:class:`django.http.HttpRequest`


Subclassing Avatar Services
---------------------------

Avatar services are intended to be subclassed. They have two attributes that
subclasses must override:

* :py:attr:`~base.AvatarService.avatar_service_id`, which is the service's
  unique identifier. This must be unique across all avatar services.

* :py:attr:`~base.AvatarService.name`, which is the service's human-readable
  name.


Subclasses must also override the
:py:meth:`~base.AvatarService.get_avatar_urls_uncached` method. This method
computes and returns the avatar URLs for the given user at a requested size
in different resolutions.

For example

.. code-block:: Python

   from django.utils.html import escape, mark_safe


   class MyAvatarService(AvatarService):
       avatar_service_id = 'my-avatar-service'
       name = 'My Avatar Service'

       def get_avatar_urls_uncached(self, user, size):
           url = 'https://example.com/avatars/%s/%d.png'
           return {
               '1x': mark_safe(url % (escape(user.username), size)),
               '2x': mark_safe(url % (escape(user.username), size * 2)),
           }

The result of this method must return Django safe text objects in the dict.
Otherwise, they may become escaped when being rendered to HTML (as the template
includes the URLs as-is).

A further example is available in :py:class:`~gravatar.GravatarService`, which
provides Gravatars as avatars.
