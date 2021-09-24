==============
Change history
==============

2.0.4
=====

*September 24, 2021*

* Translated reset password link


2.0.3
=====

*September 2, 2021*

* Removed back button everywhere (cancel does the job).
* Optimized login flow.
* Removed up/down arrows from token input field.
* Added Django admin native template integration.
* Set up automatic patching/unpatching based on setting change. This makes it 
  possible to use @override_settings in tests to control 2FA behaviour.

2.0.2
=====

*July 30 3, 2021*

* Fixed styling updates from 2.0.1.

2.0.1
=====

*July 30 3, 2021* (yanked)

* Updated default styling.

2.0.0
=====

*July 26, 2021*

* Forked from https://github.com/Bouke/django-two-factor-auth
* Change "Back to Profile" to "Back to Account Security" (part of fork master)
* Redirect to setup if 2FA is not enabled yet
* Added Django 3.x support
* Made it possible to get it working on the admin without any configuration
* Removed sniplates dependancy

Please consult the `original CHANGELOG.md`_ in the fork, up to version 1.13.

.. _`original CHANGELOG.md`: https://github.com/Bouke/django-two-factor-auth/blob/master/CHANGELOG.md
