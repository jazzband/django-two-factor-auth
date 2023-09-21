# Changelog

## 1.15.5
### Fixed
- Include transitively replaced migrations in phonenumber migration.
- Avoid importing PhoneDevice when not enabled.
- Simplified URLs for phone_create/phone_delete paths.
- Implement strict PhoneDevice identification (#661).
- Avoid multiple registrations of the same method (#657).
- Get all phonedevices of the user (#659).

### Changed
- Allow django-phonenumber-field 7.
- Updated Dutch, German, and Spanish translations.

### Removed
- Python 3.7 support (EOL).

## 1.15.4
### Fixed
- Corrected migration dependency (introduced in 6150a782b6e6).
- Fixed throttling for PhoneDevice (#418).

## 1.15.3
### Added
- Added Turkish translation.

### Fixed
- Fixed a PhoneDevice migration generated even when the phonenumber plugin was
  not installed (#587).
- Created a custom phonenumber migration to allow migration for both when the
  model already exists (legacy installs) and for new installs (#611).

## 1.15.2
### Added
- Confirmed Django 4.2 support

### Fixed
- Set `default_auto_field` to `AutoField` in apps config that have models,
  so no migrations are generated for projects defaulting to `BigAutoField` (#436).
- [webauthn] Drop unneeded unique index on `public_key`, which was unsupported
  on MySQL (#594).

## 1.15.1
### Fixed
- Missing plugin templates (#583).
- Migrations of `two_factor` app are squashed to avoid requiring `phonenumber_field`
  optional dependency for new projects.

### Changed
- Updated Finish and French translations.

## 1.15.0

### Added
- Enforcing a redirect to setup of otp device when none available for user (#499)
- Confirmed Django 4.1 support
- WebAuthn support (thanks to Javier Paniagua)
- Confirmed Python 3.11 support

### Changed 

- Display the TOTP secret key alongside the QR code to streamline setup for
  password managers without QR support.
- Moved phonenumber migrations under the plugins directory.
- Avoid crash with email devices without email (#530).

### Removed
- Django 2.2, 3.0, and 3.1 support
- `two_factor.utils.get_available_methods()` is replaced by
  `MethodRegistry.get_methods()`.

## 1.14.0

### Added
- Python 3.10 support
- The setup view got a new `secret_key` context variable to be able to display
  that key elsewhere than in the QR code.
- The token/device forms have now an `idempotent` class variable to tell if the
  form can validate more than once with the same input data.
- A new email plugin (based on django_otp `EmailDevice`) can now be activated
  and used to communicate the second factor token by email.

### Changed
- BREAKING: The phone capability moved to a plugins folder, so if you use that
  capability and want to keep it, you should add `two_factor.plugins.phonenumber`
  line in your `INSTALLED_APPS` setting. Additionally, as the `two_factor`
  templatetags library was only containing phone-related filters, the library
  was renamed to `phonenumber`.
- default_device utility function now caches the found device on the given user
  object.
- The `otp_token` form field for `AuthenticationTokenForm` is now a Django
  `RegexField` instead of an `IntegerField`.
- The Twilio gateway content for phone interaction is now template-based, and
  the pause between digits is now using the `<Pause>` tag.
- The QR code now always uses a white background to support pages displayed
  with a dark theme.

### Removed
- Python 3.5 and 3.6 support

## 1.13.2

### Added
- Translations for new languages: Hausa, Japanese, Vietnamese
- Django 4.0 support

### Changed
- Suppressed default_app_config warning on Django 3.2+
- qrcode dependency limit upped to 7.99 and django-phonenumber-field to 7
- When validating a TOTP after scanning the QR code, allow a time drift of +/-1 instead of just -1

## 1.13.1

### Add
- Support Twilio Messaging Service SID
- Add autofocus, autocomplete one-time-code and inputmode numeric to token input fields

### Changed
- Change "Back to Profile" to "Back to Account Security"

## 1.13.0

### Added
- User can request that two-factor authentication be skipped the next time they
  log in on that particular device
- Django 3.1 support
- SMS message can now be customised by using a template

### Changed
- Simplified `re_path()` to `path()` in URLConf
- Templates are now based on Bootstrap 4.
- `DisableView` now checks user has verified before disabling two-factor on
  their account
- Inline CSS has been replaced to allow stricter Content Security Policies.

### Removed
- Upper limit on django-otp dependency
- Obsolete IE<9 workarounds
- Workarounds for older versions of django-otp

## 1.12.1 - 2020-07-08

*No code changes for this version*

## 1.12 - 2020-07-08
### Added
- It is possible to set a timeout between a user authenticiating in the
  `LoginView` and them needing to re-authenticate. By default this is 10
  minutes.

### Removed
- The final step in the `LoginView` no longer re-validates a user's credentials.
- Django 1.11 support.

### Changed
- Security Fix: `LoginView` no longer stores credentials in plaintext in the
  session store.

## 1.11.0 - 2020-03-13
### Added

*Nothing has been added for this version*

### Removed
- MiddlewareMixin
- Python 3.4 support
- Django 2.1 support
- `mock` dependency

### Changed
- `extra_requires` are now listed in lowercase. This is to workaround a bug in `pip`.
- Use `trimmed` option on `blocktrans` to avoid garbage newlines in translations.
- `random_hex` from `django_otp` 0.8.0 will always return a `str`, don't try to decode it.

## 1.10.0 - 2019-12-13
### Added
- Support for Django 3.0.
- Optionally install full or light phonenumbers library.

### Removed
- Python 2 support.

### Changed
- Updated translations.

## 1.9.1 - 2019-07-07
### Changed
- 1.9.0 got pushed with incorrect changelog, no other changes.

## 1.9.0 - 2019-07-07
### Added
- Support for Django 2.2.
- Ability to create `PhoneDevice` from Django admin.
- Support for Python 3.7.

## 1.8.0 - 2018-08-03
### Added
- Support for Django 2.1.
- Support for QRcode library up to 6.
- Translation: Romanian.

### Changed
- Replace `ValidationError` with `SuspiciousOperation` in views.
- Change the wording in 2FA disable template.
- Updated translations.

## 1.7.0 - 2017-12-19
### Added
- Support for Django 2.0.

### Removed
- Django <1.11 support.

### Changed
- Do not list phone method if it is not supported (#225).
- Pass request kwarg to authentication form (#227).

## 1.6.2 - 2017-07-29
### Fixed
- Twilio client 6.0 usage (#211).

### Changed
- Updated translation: Russian.

## 1.6.1 - 2017-05-11
### Added
- Support Twilio client 6.0 (#203).

### Fixed
- `redirect_to` after successful login (#204)

### Changed
- Updated translation: Norwegian Bokmål

## 1.6.0 - 2017-04-08
### Added
- Support for Django 1.11 (#188).

### Removed
- Django 1.9 support.

### Fixed
- Allow setting `LOGIN_REDIRECT_URL` to a URL (#192).
- `DisableView` should also take `success_url` parameter (#187).

## 1.5.0 - 2017-01-04
### Added
- Django 1.10’s MIDDLEWARE support.
- Allow `success_url` overrides from `urls.py`.
- Autofocus token input during authentication.
- Translations: Polish, Italian, Hungarian, Finnish and Danish.

### Removed
- Dropped Python 3.2 and 3.3 support.

### Changed
- Renamed `redirect_url` properties to `success_url` to be consistent with Django.

### Fixed
- Allow Firefox users to enter backup tokens (#177).
- Allow multiple requests for QR code (#99).
- Don't add phone number without gateway (#92).
- Redirect to 2FA profile page after removing a phone (#159).
