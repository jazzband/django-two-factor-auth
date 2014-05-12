Class Reference
===============

Admin Site
----------
.. autoclass:: two_factor.admin.AdminSiteOTPRequired
.. autoclass:: two_factor.admin.AdminSiteOTPRequiredMixin

Decorators
----------
.. automodule:: django_otp.decorators
   :members:

.. automodule:: two_factor.views.utils
   :members: class_view_decorator

Models
------
.. autoclass:: two_factor.models.PhoneDevice
.. autoclass:: django_otp.plugins.otp_static.models.StaticDevice
.. autoclass:: django_otp.plugins.otp_static.models.StaticToken
.. autoclass:: django_otp.plugins.otp_totp.models.TOTPDevice

Middleware
----------
.. autoclass:: django_otp.middleware.OTPMiddleware

Signals
-------
.. module:: two_factor.signals
.. data:: user_verified

   Sent when a user is verified against a OTP device. Provides the following
   arguments:

   ``sender``
       The class sending the signal (``'two_factor.views.core'``).

   ``user``
       The user that was verified.

   ``device``
       The OTP device that was used.


   ``request``
       The ``HttpRequest`` in which the user was verified.

Template Tags
-------------
.. automodule:: two_factor.templatetags.two_factor
   :members:

Views
-----
.. autoclass:: two_factor.views.LoginView
.. autoclass:: two_factor.views.SetupView
.. autoclass:: two_factor.views.SetupCompleteView
.. autoclass:: two_factor.views.BackupTokensView
.. autoclass:: two_factor.views.PhoneSetupView
.. autoclass:: two_factor.views.PhoneDeleteView
.. autoclass:: two_factor.views.ProfileView
.. autoclass:: two_factor.views.DisableView

View Mixins
-----------
.. automodule:: two_factor.views.mixins
   :members:
