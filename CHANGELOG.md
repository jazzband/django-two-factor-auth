## [Unreleased]

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
