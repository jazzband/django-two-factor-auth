Release Notes
=============

1.0.0-beta3
-----------
* Fixed #62 -- Don't leak sensitive post parameters
* Fixed #63 -- Login wizard should handle changing passwords

1.0.0-beta2
-----------
* Fixed #60 -- Always cast the token to an int before verification

1.0.0-beta1
-----------
* Support for Django 1.7
* New translations: German, Spanish, French, Swedish and Portuguese (Brazil)
* #39 -- Added support for custom user model (Django 1.5+)
* Added management commands
* Added support for YubiKeys
* Fire signal when user is verified
* #44 -- Don't require re-login after setup
* #49 -- Advise to add backup devices after setup
* #52 -- Add URL encoding to otpauth URL
* #54 -- Mitigate voicemail hack
* #55 -- Use two_factor:login instead of LOGIN_URL

0.5.0
-----
* #32 -- Make the auth method label capitalization more consistent
* #31 -- Set an error code for phone_number_validator
* #30 -- Don't transmit token seed through GET parameters
* #29 -- Generate QR codes locally
* #27 -- South migrations to support custom user model

0.4.0
-----
* Fixed #26 -- Twilio libraries are required

0.3.1
-----
* Fixed #25 -- Back-up tokens cannot be used for login

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
