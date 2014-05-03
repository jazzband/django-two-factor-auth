Release Notes
=============

0.6.0 (in development)
----------------------
* Support for Django 1.7
* Fixed #39 -- Added support for custom user model (Django 1.5+)

0.5.0
-----
* Fixed #32 -- Make the auth method label capitalization more consistent (thanks to Christian Hammond)
* Fixed #31 -- Set an error code for phone_number_validator (thanks to Christian Hammond)
* Fixed #30 -- Don't transmit token seed through GET parameters (thanks to Daniel Hall)
* Fixed #29 -- Generate QR codes locally (thanks to Daniel Hall)
* Fixed #27 -- South migrations to support custom user model (thanks to Agris Ameriks)

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
