Usage
=====
Users can opt-in to enhanced security by enabling two-factor authentication.
There is currently no enforcement of a policy, it is entirely optional.
However, you could override this behaviour to enforce a custom policy.

Limiting access to certain views
--------------------------------
For increased security views can be limited to two-factor-enabled users. This
allows you to secure certain parts of the website. Doing so requires a
decorator, class mixin or a custom inspection of a user's session.

Decorator
~~~~~~~~~
You can use django-otp's built-in :meth:`~django_otp.decorators.otp_required`
decorator to limit access to two-factor-enabled users::

    from django_otp.decorators import otp_required

    @otp_required
    def my_view(request):
        pass

Use :meth:`~two_factor.views.utils.class_view_decorator` for decorating
class-based views (CBVs)::

    from two_factor.views.utils import class_view_decorator

    @class_view_decorator(otp_required)
    class MyView(TemplateView):
        pass

Mixin
~~~~~
.. note::
  A mixin class is not (yet) available.

Custom
~~~~~~
The method ``is_verified()`` is added through django-otp's
:class:`~django_otp.middleware.OTPMiddleware` which can be used to check if the
user was logged in using two-factor authentication::

    def my_view(request):
        if request.user.is_verified():
            # user logged in using two-factor
            pass
        else:
            # user not logged in using two-factor
            pass

Enforcing two-factor
--------------------
Forcing users to enable two-factor authentication is not implemented. However,
you could create your own custom policy.
