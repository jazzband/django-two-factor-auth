Release Notes
=============

1.7.0
-----
* New: Support for Django 2.0.
* Dropped Django <1.11 support.
* Fix: Do not list phone method if it is not supported (#225).
* Pass request kwarg to authentication form (#227).

1.6.2
-----
* Fix: Twilio client 6.0 usage (#211).
* Updated translation: Russian.

1.6.1
-----
* Support Twilio client 6.0 (#203).
* Fix: Fixed redirect_to after successful login (#204).
* Updated translation: Norwegian Bokmål.

1.6.0
-----
* New: Support for Django 1.11 (#188).
* Dropped Django 1.9 support.
* Fix: Allow setting ``LOGIN_REDIRECT_URL`` to a URL (#192).
* Fix: ``DisableView`` should also take ``success_url`` parameter (#187).

1.5.0
-----
* New: Django 1.10’s MIDDLEWARE support.
* New: Allow ``success_url`` overrides from ``urls.py``.
* New: Autofocus token input during authentication.
* New translations: Polish, Italian, Hungarian, Finnish and Danish.
* Renamed ``redirect_url`` properties to ``success_url`` to be consistent with Django.
* Dropped Python 3.2 and 3.3 support.
* Fix: Allow Firefox users to enter backup tokens (#177).
* Fix: Allow multiple requests for QR code (#99).
* Fix: Don't add phone number without gateway (#92).
* Fix: Redirect to 2FA profile page after removing a phone (#159).

1.4.0
-----
* New: Support for Django 1.10 (#157).
* Fix: Enable autodoc builds in documentation (#164).
* Fix: Support named urls in ``LOGIN_URL``, ``LOGIN_REDIRECT_URL`` and
  ``LOGOUT_URL`` (#153).

1.3.1
-----
* Fix: KeyError when trying to login (#102).
* Fix: Migration fails with custom user model without username field.
* Fix: Added missing migrations.
* Fix: Spurious migrations on Python 3.
* Require django-otp 0.3.4 and above for better Python 3 compatibility.

1.3.0
-----
* New feature: Added support for Django 1.9.
* New feature: Use phonenumbers library to validate phone number format.
* New feature: Use django-phonenumber-field for storing phone number in E.164 format.
* Use AppConfig for patching admin.
* Reduced number of tox test environments.
* Removed support for Django 1.7 and below.
* Fix: Catch gateway errors.
* Fix: Use raw_id_fields on admin site form.
* Fix: Skip test that hits bug in Python 2.7.10.
* Fix: Import changed in django-otp 0.3.?.

1.2.2
-----
* Allow django-otp 0.3.x as well as 0.2.x.

1.2.1
-----
* Fix: Resolved an issue with django_otp 0.3.2 and higher.

1.2.0
-----
* Fix: Issue with migrations on Py3 (#87).
* Fix: Fixed failing migration on Django 1.7.0 (#83).
* Fix: Issue with pip unable to install package.
* Dropped support for Django 1.5 and 1.6.
* Added support for Django 1.8.

1.1.1
-----
* Fix: Resolved a warning from Django 1.7 migrations (#80).

1.1.0
-----
* New feature: Django 1.7 migrations.
* New feature: Optional support for 8 digit codes (#79).
* Renamed management commands (#77).
* Fix: If the login view state was reset, an exception was raised (#65).
* Fix: Off-screen buttons in default template were visibile on screens with
  high resolution (#76).

1.0.0
-----
* New translations: German, Spanish, French, Swedish and Portuguese (Brazil).
* New feature: Support for Django 1.7.
* New feature: Management commands.
* New feature: Support for YubiKeys.
* New feature: Support for custom user model (Django 1.5+) (#39).
* Auto-login after completing setup (#44).
* Advise to add backup devices after setup (#49).
* Documentation about securing admindocs (#66).
* Mitigate voicemail hack (#54).
* Fire signal when user is verified.
* Fix: Cannot generate QR code for unicode characters (#69).
* Fix: Secure sensitive post parameters (#62).
* Fix: Login wizard should handle changing passwords (#63).
* Fix: Always cast the token to an int before verification (#60).
* Fix: Add URL encoding to otpauth URL (#52).
* Fix: Use two_factor:login instead of LOGIN_URL (#55).

0.5.0
-----
* #32 -- Make the auth method label capitalization more consistent.
* #31 -- Set an error code for phone_number_validator.
* #30 -- Don't transmit token seed through GET parameters.
* #29 -- Generate QR codes locally.
* #27 -- South migrations to support custom user model.

0.4.0
-----
* Fixed #26 -- Twilio libraries are required.

0.3.1
-----
* Fixed #25 -- Back-up tokens cannot be used for login.

0.3.0
-----
* #18 -- Optionally enforce OTP for admin views.
* New translation: Simplified Chinese.

0.2.3
-----
* Two new translations: Hebrew and Arabic.

0.2.2
-----
* Allow changing Twilio call language.

0.2.1
-----
* Allow overriding instructions in the template.
* Allow customization of the redirect query parameter.
* Faster backup token generating.

0.2.0
-----
This is a major upgrade, as the package has been rewritten completely. Upgrade
to this version with care and make backups of your database before running the
South migrations. See installation instructions for installing the new version;
update your template customizations and run the database migrations.
