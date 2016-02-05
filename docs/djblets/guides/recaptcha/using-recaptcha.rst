.. _using-recaptcha:

===============
Using reCAPTCHA
===============

.. currentmodule:: djblets.recaptcha


Using reCAPTCHA validation in forms requires valid reCAPTCHA secret and site
keys. You can get keys from https://www.google.com/recaptcha/.

The keys can be stored in either Django settings or
:py:mod:`site configuration settings <djblets.siteconfig.models>`. The keys for
Django settings are:

* ``RECAPTCHA_PUBLIC_KEY``
* ``RECPATCHA_PRIVATE_KEY``

The equivalent site configuration keys are:

* ``recaptcha_public_key``
* ``recaptcha_private_key``


reCAPTCHA in Forms
------------------

If you want to use reCAPTCHA in a form, that form will have to inherit from the
:py:class:`~mixins.RecaptchaFormMixin` (as well as
:py:class:`~django.forms.Form`).
Your form can optionally provide a property,
:py:meth:`~mixins.RecaptchaFormMixin.verify_recaptcha`, which will determine
whether or not to validate the reCAPTCHA when the form is submitted. This can
be used to optionally disable reCAPTCHA through a setting, for example.

Your form will require special rendering to use reCAPTCHA. The
:py:mod:`~djblets.recaptcha.templatetags.djblets_recaptcha` template tag
library includes two template tags to help with this:

* :py:meth:`~templatetags.djblets_recaptcha.recaptcha_js`, which renders the
  necessary JavaScript to use reCAPTCHA on the page. This should be included
  in the ``<head>`` of your document.

* :py:meth:`~templatetags.djblets_recaptcha.recaptcha_form_field`, which
  renders the actual reCAPTCHA field. This should be included in your form,
  before the ``<input type="submit">`` tag.


Using Site Configuration
------------------------

To use site configuration settings instead of Django settings, you will have to
load the settings map for this module. This should happen once your app is
initialized. An example using an :py:class:`django.apps.AppConfig` follows:

.. code-block:: python

   from django.apps import AppConfig
   from djblets.siteconfig.django_settings import (apply_django_settings,
                                                   generate_defaults,
                                                   get_django_defaults,
                                                   get_django_settings_map)
   from djblets.recaptcha import (defaults as recaptcha_defaults,
                                  settings_map as recaptcha_settings_map)

   class MyAppConfig(AppConfig):
       def ready(self):
           if not siteconfig.get_defaults():
               defaults = get_django_defaults()
               defaults.update(recaptcha_defaults)

               siteconfig.add_defaults(defaults)

           settings_map = get_django_settings_map()
           settings_map.update(recaptcha_settings_map)

           apply_django_settings(settings_map)


Using reCAPTCHA in a Form Template
----------------------------------

If you are not using customized form rendering (i.e. you are rendering your
form as ``{{form}}`` in your template, you can continue to do so; just ensure
that the :py:meth:`~templatetags.djblets_recaptcha.recaptcha_js` template tag
appears in the document ``<head>``. However, if you are rendering your form
fields individually, you will have to use the
:py:meth:`~templatetags.djblets_recaptcha.recaptcha_form_field` template tag.

For example, consider the following form:

.. code-block:: python

   from django import forms
   from django.forms import fields
   from djblets.recaptcha.mixins import RecaptchaFormMixin


   class RegistrationForm(RecaptchaFormMixin, forms.Form):
       username = fields.CharField(max_length=32,
                                   label='Username')
       password = fields.CharField(min_length=8,
                                   label='Password',
                                   widget=forms.PasswordInput)

The following two templates can be used to render the form, assuming ``form``
is the instance of the form. The first template shows rendering using Django's
built-in form rendering:

.. code-block:: html

   {% load djblets_recaptcha %}

   <!DOCTYPE html>
   <html>
    <head>
     <title>Register</title>
     {% recaptcha_js %}
    </head>
    <body>
     {{form}}
    </body>
   </html>

The second example shows how to use direct field rendering:

.. code-block:: html

   {% load djblets_recaptcha %}

   <!DOCTYPE html>
   <html>
    <head>
     <title>Register</title>
     {% recaptcha_js %}
    </head>
    <body>
     <form method="POST" action="." id="register-form">
      <div class="row">
       {{form.username.label_tag}}
       {{form.username}}
       {{form.errors.username
      </div>
      <div class="row">
       {{form.password.label_tag}}
       {{form.password}}
       {{form.errors.password}}
      </div>
      <div class="row">
       {% recaptcha_form_field form %}
      </div>
      <div class="row">
       <input type="submit" value="Register">
      </div>
     </form>
    </body>
   </html>


Styling reCAPTCHA fields
------------------------

The reCAPTCHA field will render as a ``<div>`` element with the class
``g-recaptcha`` if you wish to style it.
