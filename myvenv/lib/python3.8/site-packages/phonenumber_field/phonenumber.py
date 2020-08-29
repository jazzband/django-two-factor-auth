import phonenumbers
from django.conf import settings
from django.core import validators


class PhoneNumber(phonenumbers.PhoneNumber):
    """
    A extended version of phonenumbers.PhoneNumber that provides
    some neat and more pythonic, easy to access methods. This makes using a
    PhoneNumber instance much easier, especially in templates and such.
    """

    format_map = {
        "E164": phonenumbers.PhoneNumberFormat.E164,
        "INTERNATIONAL": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
        "NATIONAL": phonenumbers.PhoneNumberFormat.NATIONAL,
        "RFC3966": phonenumbers.PhoneNumberFormat.RFC3966,
    }

    @classmethod
    def from_string(cls, phone_number, region=None):
        phone_number_obj = cls()
        if region is None:
            region = getattr(settings, "PHONENUMBER_DEFAULT_REGION", None)
        phonenumbers.parse(
            number=phone_number,
            region=region,
            keep_raw_input=True,
            numobj=phone_number_obj,
        )
        return phone_number_obj

    def __str__(self):
        format_string = getattr(settings, "PHONENUMBER_DEFAULT_FORMAT", "E164")
        fmt = self.format_map[format_string]
        return self.format_as(fmt)

    def is_valid(self):
        """
        checks whether the number supplied is actually valid
        """
        return phonenumbers.is_valid_number(self)

    def format_as(self, format):
        return phonenumbers.format_number(self, format)

    @property
    def as_international(self):
        return self.format_as(phonenumbers.PhoneNumberFormat.INTERNATIONAL)

    @property
    def as_e164(self):
        return self.format_as(phonenumbers.PhoneNumberFormat.E164)

    @property
    def as_national(self):
        return self.format_as(phonenumbers.PhoneNumberFormat.NATIONAL)

    @property
    def as_rfc3966(self):
        return self.format_as(phonenumbers.PhoneNumberFormat.RFC3966)

    def __len__(self):
        return len(str(self))

    def __eq__(self, other):
        """
        Override parent equality because we store only string representation
        of phone number, so we must compare only this string representation
        """
        if isinstance(other, (str, phonenumbers.PhoneNumber)):
            format_string = getattr(settings, "PHONENUMBER_DB_FORMAT", "E164")
            default_region = getattr(settings, "PHONENUMBER_DEFAULT_REGION", None)
            fmt = self.format_map[format_string]
            if isinstance(other, str):
                # convert string to phonenumbers.PhoneNumber
                # instance
                try:
                    other = phonenumbers.parse(other, region=default_region)
                except phonenumbers.NumberParseException:
                    # Conversion is not possible, thus not equal
                    return False
            other_string = phonenumbers.format_number(other, fmt)
            return self.format_as(fmt) == other_string
        else:
            return False

    def __hash__(self):
        return hash(str(self))


def to_python(value, region=None):
    if value in validators.EMPTY_VALUES:  # None or ''
        phone_number = value
    elif isinstance(value, str):
        try:
            phone_number = PhoneNumber.from_string(phone_number=value, region=region)
        except phonenumbers.NumberParseException:
            # the string provided is not a valid PhoneNumber.
            phone_number = PhoneNumber(raw_input=value)
    elif isinstance(value, PhoneNumber):
        phone_number = value
    elif isinstance(value, phonenumbers.PhoneNumber):
        phone_number = PhoneNumber()
        phone_number.merge_from(value)
    else:
        raise TypeError("Can't convert %s to PhoneNumber." % type(value).__name__)
    return phone_number


def validate_region(region):
    if (
        region is not None
        and region not in phonenumbers.shortdata._AVAILABLE_REGION_CODES
    ):
        raise ValueError(
            "“%s” is not a valid region code. Choices are %r"
            % (region, phonenumbers.shortdata._AVAILABLE_REGION_CODES)
        )
