import re


class NumericFunction:

    """
    This is a class that provides a numeric function for version parts.
    It simply starts with the provided first_value (0 by default) and
    increases it following the sequence of integer numbers.

    The optional value of this function is equal to the first value.

    This function also supports alphanumeric parts, altering just the numeric
    part (e.g. 'r3' --> 'r4'). Only the first numeric group found in the part is
    considered (e.g. 'r3-001' --> 'r4-001').
    """

    FIRST_NUMERIC = re.compile(r"([^\d]*)(\d+)(.*)")

    def __init__(self, first_value=None):

        if first_value is not None:
            try:
                _, _, _ = self.FIRST_NUMERIC.search(
                    first_value
                ).groups()
            except AttributeError:
                raise ValueError(
                    "The given first value {} does not contain any digit".format(first_value)
                )
        else:
            first_value = 0

        self.first_value = str(first_value)
        self.optional_value = self.first_value

    def bump(self, value):
        part_prefix, part_numeric, part_suffix = self.FIRST_NUMERIC.search(
            value
        ).groups()
        bumped_numeric = int(part_numeric) + 1

        return "".join([part_prefix, str(bumped_numeric), part_suffix])


class ValuesFunction:

    """
    This is a class that provides a values list based function for version parts.
    It is initialized with a list of values and iterates through them when
    bumping the part.

    The default optional value of this function is equal to the first value,
    but may be otherwise specified.

    When trying to bump a part which has already the maximum value in the list
    you get a ValueError exception.
    """

    def __init__(self, values, optional_value=None, first_value=None):

        if not values:
            raise ValueError("Version part values cannot be empty")

        self._values = values

        if optional_value is None:
            optional_value = values[0]

        if optional_value not in values:
            raise ValueError(
                "Optional value {} must be included in values {}".format(
                    optional_value, values
                )
            )

        self.optional_value = optional_value

        if first_value is None:
            first_value = values[0]

        if first_value not in values:
            raise ValueError(
                "First value {} must be included in values {}".format(
                    first_value, values
                )
            )

        self.first_value = first_value

    def bump(self, value):
        try:
            return self._values[self._values.index(value) + 1]
        except IndexError:
            raise ValueError(
                "The part has already the maximum value among {} and cannot be bumped.".format(
                    self._values
                )
            )
