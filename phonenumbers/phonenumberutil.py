"""Python phone number parsing and formatting library"""

# Based on original Java code:
#     java/src/com/google/i18n/phonenumbers/PhoneNumberUtil.java
#   Copyright (C) 2009-2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re

# Extra regexp function; see README
from re_util import fullmatch

# Data class definitions
from phonenumber import PhoneNumber, CountryCodeSource
from phonemetadata import NumberFormat, PhoneMetadata

# Import auto-generated data structures
try:
    from data import _COUNTRY_CODE_TO_REGION_CODE
except ImportError:  # pragma no cover
    # Before the generated code exists, the data/ directory is empty.
    # The generation process imports this module, creating a circular
    # dependency.  The hack below works around this.
    import os
    import sys
    if os.path.basename(sys.argv[0]) == "buildmetadatafromxml.py":
        print >> sys.stderr, "Failed to import generated data (but OK as during autogeneration)"
        _COUNTRY_CODE_TO_REGION_CODE = {1: ("US")}
    else:
        raise

# Set the master map from country code to region code.  The
# extra level of indirection allows the unit test to replace
# the map with test data.
COUNTRY_CODE_TO_REGION_CODE = _COUNTRY_CODE_TO_REGION_CODE

# Naming convention for phone number arguments and variables:
#  - string arguments are named 'number'
#  - PhoneNumber objects are named 'numobj'

# Flags to use when compiling regular expressions for phone numbers.
_REGEX_FLAGS = re.UNICODE | re.IGNORECASE
# The minimum and maximum length of the national significant number.
_MIN_LENGTH_FOR_NSN = 3
_MAX_LENGTH_FOR_NSN = 15
# The maximum length of the country calling code.
_MAX_LENGTH_COUNTRY_CODE = 3
# Region-code for the unknown region.
UNKNOWN_REGION = u"ZZ"
# The set of regions that share country code 1.
_NANPA_COUNTRY_CODE = 1
# The PLUS_SIGN signifies the international prefix.
_PLUS_SIGN = u'+'
_RFC3966_EXTN_PREFIX = u";ext="

# Simple ASCII digits map used to populate _DIGIT_MAPPINGS and
# _ALL_PLUS_NUMBER_GROUPING_SYMBOLS.
_ASCII_DIGITS_MAP = {u'0': u'0', u'1': u'1',
                     u'2': u'2', u'3': u'3',
                     u'4': u'4', u'5': u'5',
                     u'6': u'6', u'7': u'7',
                     u'8': u'8', u'9': u'9'}

# These mappings map a character (key) to a specific digit that should replace
# it for normalization purposes. Non-European digits that may be used in phone
# numbers are mapped to a European equivalent.
_DIGIT_MAPPINGS = dict({u'\uFF10': u'0',  # Fullwidth digit 0
                        u'\u0660': u'0',  # Arabic-indic digit 0
                        u'\u06F0': u'0',  # Eastern-Arabic digit 0
                        u'\uFF11': u'1',  # Fullwidth digit 1
                        u'\u0661': u'1',  # Arabic-indic digit 1
                        u'\u06F1': u'1',  # Eastern-Arabic digit 1
                        u'\uFF12': u'2',  # Fullwidth digit 2
                        u'\u0662': u'2',  # Arabic-indic digit 2
                        u'\u06F2': u'2',  # Eastern-Arabic digit 2
                        u'\uFF13': u'3',  # Fullwidth digit 3
                        u'\u0663': u'3',  # Arabic-indic digit 3
                        u'\u06F3': u'3',  # Eastern-Arabic digit 3
                        u'\uFF14': u'4',  # Fullwidth digit 4
                        u'\u0664': u'4',  # Arabic-indic digit 4
                        u'\u06F4': u'4',  # Eastern-Arabic digit 4
                        u'\uFF15': u'5',  # Fullwidth digit 5
                        u'\u0665': u'5',  # Arabic-indic digit 5
                        u'\u06F5': u'5',  # Eastern-Arabic digit 5
                        u'\uFF16': u'6',  # Fullwidth digit 6
                        u'\u0666': u'6',  # Arabic-indic digit 6
                        u'\u06F6': u'6',  # Eastern-Arabic digit 6
                        u'\uFF17': u'7',  # Fullwidth digit 7
                        u'\u0667': u'7',  # Arabic-indic digit 7
                        u'\u06F7': u'7',  # Eastern-Arabic digit 7
                        u'\uFF18': u'8',  # Fullwidth digit 8
                        u'\u0668': u'8',  # Arabic-indic digit 8
                        u'\u06F8': u'8',  # Eastern-Arabic digit 8
                        u'\uFF19': u'9',  # Fullwidth digit 9
                        u'\u0669': u'9',  # Arabic-indic digit 9
                        u'\u06F9': u'9',  # Eastern-Arabic digit 9
                        }, **_ASCII_DIGITS_MAP)

# Only upper-case variants of alpha characters are stored.
_ALPHA_MAPPINGS = {u'A': u'2',
                   u'B': u'2',
                   u'C': u'2',
                   u'D': u'3',
                   u'E': u'3',
                   u'F': u'3',
                   u'G': u'4',
                   u'H': u'4',
                   u'I': u'4',
                   u'J': u'5',
                   u'K': u'5',
                   u'L': u'5',
                   u'M': u'6',
                   u'N': u'6',
                   u'O': u'6',
                   u'P': u'7',
                   u'Q': u'7',
                   u'R': u'7',
                   u'S': u'7',
                   u'T': u'8',
                   u'U': u'8',
                   u'V': u'8',
                   u'W': u'9',
                   u'X': u'9',
                   u'Y': u'9',
                   u'Z': u'9', }
# For performance reasons, amalgamate both into one map.
_ALL_NORMALIZATION_MAPPINGS = dict(_ALPHA_MAPPINGS, **_DIGIT_MAPPINGS)

# Separate map of all symbols that we wish to retain when formatting alpha
# numbers. This includes digits, ASCII letters and number grouping symbols
# such as "-" and " ".
_ALL_PLUS_NUMBER_GROUPING_SYMBOLS = dict({u'-': u'-',  # Put grouping symbols.
                                          u'\uFF0D': u'-',
                                          u'\u2010': u'-',
                                          u'\u2011': u'-',
                                          u'\u2012': u'-',
                                          u'\u2013': u'-',
                                          u'\u2014': u'-',
                                          u'\u2015': u'-',
                                          u'\u2212': u'-',
                                          u'/': u'/',
                                          u'\uFF0F': u'/',
                                          u' ': u' ',
                                          u'\u3000': u' ',
                                          u'\u2060': u' ',
                                          u'.': u'.',
                                          u'\uFF0E': u'.'},
                                         # Put (lower letter -> upper letter) and
                                         # (upper letter -> upper letter) mappings.
                                         **dict([(_c.lower(), _c) for _c in _ALPHA_MAPPINGS.keys()] +
                                                [(_c, _c)         for _c in _ALPHA_MAPPINGS.keys()],
                                                **_ASCII_DIGITS_MAP))

# Pattern that makes it easy to distinguish whether a region has a unique
# international dialing prefix or not. If a region has a unique international
# prefix (e.g. 011 in USA), it will be represented as a string that contains a
# sequence of ASCII digits. If there are multiple available international
# prefixes in a region, they will be represented as a regex string that always
# contains character(s) other than ASCII digits.  Note this regex also
# includes tilde, which signals waiting for the tone.
_UNIQUE_INTERNATIONAL_PREFIX = re.compile(u"[\\d]+(?:[~\u2053\u223C\uFF5E][\\d]+)?")

# Regular expression of acceptable punctuation found in phone numbers. This
# excludes punctuation found as a leading character only.  This consists of
# dash characters, white space characters, full stops, slashes, square
# brackets, parentheses and tildes. It also includes the letter 'x' as that is
# found as a placeholder for carrier information in some phone numbers.
_VALID_PUNCTUATION = (u"-x\u2010-\u2015\u2212\u30FC\uFF0D-\uFF0F " +
                      u"\u00A0\u200B\u2060\u3000()\uFF08\uFF09\uFF3B\uFF3D.\\[\\]/~\u2053\u223C\uFF5E")

# Digits accepted in phone numbers that we understand.
_VALID_DIGITS = ''.join(_DIGIT_MAPPINGS.keys())
# We accept alpha characters in phone numbers, ASCII only, upper and lower
# case.
_VALID_ALPHA = (''.join(_ALPHA_MAPPINGS.keys()) +
                ''.join([_k.lower() for _k in _ALPHA_MAPPINGS.keys()]))
_PLUS_CHARS = u"+\uFF0B"
_PLUS_CHARS_PATTERN = re.compile(u"[" + _PLUS_CHARS + u"]+")
_SEPARATOR_PATTERN = re.compile(u"[" + _VALID_PUNCTUATION + u"]+")
_CAPTURING_DIGIT_PATTERN = re.compile(u"([" + _VALID_DIGITS + u"])")

# Regular expression of acceptable characters that may start a phone number
# for the purposes of parsing. This allows us to strip away meaningless
# prefixes to phone numbers that may be mistakenly given to us. This consists
# of digits, the plus symbol and arabic-indic digits. This does not contain
# alpha characters, although they may be used later in the number. It also
# does not include other punctuation, as this will be stripped later during
# parsing and is of no information value when parsing a number.
_VALID_START_CHAR = u"[" + _PLUS_CHARS + _VALID_DIGITS + u"]"
_VALID_START_CHAR_PATTERN = re.compile(_VALID_START_CHAR)

# Regular expression of characters typically used to start a second phone
# number for the purposes of parsing. This allows us to strip off parts of the
# number that are actually the start of another number, such as for: (530)
# 583-6985 x302/x2303 -> the second extension here makes this actually two
# phone numbers, (530) 583-6985 x302 and (530) 583-6985 x2303. We remove the
# second extension so that the first number is parsed correctly.
_SECOND_NUMBER_START = u"[\\\\/] *x"
_SECOND_NUMBER_START_PATTERN = re.compile(_SECOND_NUMBER_START)

# Regular expression of trailing characters that we want to remove. We remove
# all characters that are not alpha or numerical characters. The hash
# character is retained here, as it may signify the previous block was an
# extension.
#
# The original Java regexp is:
#   [[\\P{N}&&\\P{L}]&&[^#]]+$
# which splits out as:
#   [                      ]+$  : >=1 of the following chars at end of string
#    [              ]&&[  ]     : intersection of these two sets of chars
#    [      &&      ]           : intersection of these two sets of chars
#     \\P{N}                    : characters without the "Number" Unicode property
#              \\P{L}           : characters without the "Letter" Unicode property
#                      [^#]     : character other than hash
# which nets down to: >=1 non-Number, non-Letter, non-# characters at string end
# In Python Unicode regexp mode '(?u)', the class '[^#\w]' will match anything
# that is not # and is not alphanumeric and is not underscore.
_UNWANTED_END_CHARS = '(?u)(?:_|[^#\w])+$'
_UNWANTED_END_CHAR_PATTERN = re.compile(_UNWANTED_END_CHARS)

# We use this pattern to check if the phone number has at least three letters
# in it - if so, then we treat it as a number where some phone-number digits
# are represented by letters.
_VALID_ALPHA_PHONE_PATTERN = re.compile(u"(?:.*?[A-Za-z]){3}.*")

# Regular expression of viable phone numbers. This is location
# independent. Checks we have at least three leading digits, and only valid
# punctuation, alpha characters and digits in the phone number. Does not
# include extension data.  The symbol 'x' is allowed here as valid punctuation
# since it is often used as a placeholder for carrier codes, for example in
# Brazilian phone numbers. We also allow multiple "+" characters at the start.
# Corresponds to the following:
# plus_sign*([punctuation]*[digits]){3,}([punctuation]|[digits]|[alpha])*
# Note VALID_PUNCTUATION starts with a -, so must be the first in the range.
_VALID_PHONE_NUMBER = (u"[" + _PLUS_CHARS + u"]*(?:[" + _VALID_PUNCTUATION + u"]*[" + _VALID_DIGITS + u"]){3,}[" +
                       _VALID_PUNCTUATION + _VALID_ALPHA + _VALID_DIGITS + u"]*")

# Default extension prefix to use when formatting. This will be put in front
# of any extension component of the number, after the main national number is
# formatted. For example, if you wish the default extension formatting to be
# " extn: 3456", then you should specify " extn: " here as the default
# extension prefix. This can be overridden by region-specific preferences.
_DEFAULT_EXTN_PREFIX = u" ext. "

# Regexp of all possible ways to write extensions, for use when parsing. This
# will be run as a case-insensitive regexp match. Wide character versions are
# also provided after each ASCII version. There are three regular expressions
# here. The first covers RFC 3966 format, where the extension is added using
# ";ext=". The second more generic one starts with optional white space and
# ends with an optional full stop (.), followed by zero or more spaces/tabs
# and then the numbers themselves. The other one covers the special case of
# American numbers where the extension is written with a hash at the end, such
# as "- 503#".  Note that the only capturing groups should be around the
# digits that you want to capture as part of the extension, or else parsing
# will fail!  Canonical-equivalence doesn't seem to be an option with Android
# java, so we allow two options for representing the accented o - the
# character itself, and one in the unicode decomposed form with the combining
# acute accent.
_CAPTURING_EXTN_DIGITS = u"([" + _VALID_DIGITS + u"]{1,7})"
_KNOWN_EXTN_PATTERNS = (_RFC3966_EXTN_PREFIX + _CAPTURING_EXTN_DIGITS + u"|" +
                        u"[ \u00A0\\t,]*(?:ext(?:ensi(?:o\u0301?|\u00F3))?n?|" +
                        u"\uFF45\uFF58\uFF54\uFF4E?|[,x\uFF58#\uFF03~\uFF5E]|int|anexo|\uFF49\uFF4E\uFF54)" +
                        u"[:\\.\uFF0E]?[ \u00A0\\t,-]*" + _CAPTURING_EXTN_DIGITS + u"#?|" +
                        u"[- ]+([" + _VALID_DIGITS + u"]{1,5})#")

# Regexp of all known extension prefixes used by different regions followed by
# 1 or more valid digits, for use when parsing.
_EXTN_PATTERN = re.compile(u"(?:" + _KNOWN_EXTN_PATTERNS + u")$", _REGEX_FLAGS)

# We append optionally the extension pattern to the end here, as a valid phone
# number may have an extension prefix appended, followed by 1 or more digits.
_VALID_PHONE_NUMBER_PATTERN = re.compile(_VALID_PHONE_NUMBER + u"(?:" + _KNOWN_EXTN_PATTERNS + u")?", _REGEX_FLAGS)

# We use a non-capturing group because Python's re.split() returns any capturing
# groups interspersed with the other results (unlike Java's Pattern.split()).
_NON_DIGITS_PATTERN = re.compile("(?:\\D+)")

# The FIRST_GROUP_PATTERN was originally set to \1 but there are some
# countries for which the first group is not used in the national pattern
# (e.g. Argentina) so the \1 group does not match correctly.  Therefore, we
# use \d, so that the first group actually used in the pattern will be
# matched.
_FIRST_GROUP_PATTERN = re.compile(r"(\\\d)")
_NP_PATTERN = re.compile("\\$NP")
_FG_PATTERN = re.compile("\\$FG")
_CC_PATTERN = re.compile("\\$CC")


class PhoneNumberFormat(object):
    """
    Phone number format.

    INTERNATIONAL and NATIONAL formats are consistent with the definition in
    ITU-T Recommendation E. 123. For example, the number of the Google Zurich
    office will be written as "+41 44 668 1800" in INTERNATIONAL format, and
    as "044 668 1800" in NATIONAL format.  E164 format is as per INTERNATIONAL
    format but with no formatting applied, e.g. +41446681800.  RFC3966 is as
    per INTERNATIONAL format, but with all spaces and other separating symbols
    replaced with a hyphen, and with any phone number extension appended with
    ";ext=".

    Note: If you are considering storing the number in a neutral format, you
    are highly advised to use the PhoneNumber class.
    """
    E164 = 0
    INTERNATIONAL = 1
    NATIONAL = 2
    RFC3966 = 3


class PhoneNumberType(object):
    """Type of phone numbers."""
    FIXED_LINE = 0
    MOBILE = 1
    # In some regions (e.g. the USA), it is impossible to distinguish between
    # fixed-line and mobile numbers by looking at the phone number itself.
    FIXED_LINE_OR_MOBILE = 2
    # Freephone lines
    TOLL_FREE = 3
    PREMIUM_RATE = 4
    # The cost of this call is shared between the caller and the recipient,
    # and is hence typically less than PREMIUM_RATE calls. See
    # http://en.wikipedia.org/wiki/Shared_Cost_Service for more information.
    SHARED_COST = 5
    # Voice over IP numbers. This includes TSoIP (Telephony Service over IP).
    VOIP = 6
    # A personal number is associated with a particular person, and may be
    # routed to either a MOBILE or FIXED_LINE number. Some more information
    # can be found here: http://en.wikipedia.org/wiki/Personal_Numbers
    PERSONAL_NUMBER = 7
    PAGER = 8
    # Used for "Universal Access Numbers" or "Company Numbers". They may be
    # further routed to specific offices, but allow one number to be used for
    # a company.
    UAN = 9
    # A phone number is of type UNKNOWN when it does not fit any of the known
    # patterns for a specific region.
    UNKNOWN = 10


class MatchType(object):
    """Types of phone number matches."""
    # Not a telephone number
    NOT_A_NUMBER = 0
    # None of the match types below apply
    NO_MATCH = 1
    # Returns SHORT_NSN_MATCH if either or both has no region specified, or
    # the region specified is the same, and one NSN could be a shorter version
    # of the other number. This includes the case where one has an extension
    # specified, and the other does not.
    SHORT_NSN_MATCH = 2
    # Either or both has no region specified, and the NSNs and extensions are
    # the same.
    NSN_MATCH = 3

    # The country_code, NSN, presence of a leading zero for Italian numbers
    # and any extension present are the same.
    EXACT_MATCH = 4


class ValidationResult(object):
    """Possible outcomes when testing if a PhoneNumber is a possible number."""
    IS_POSSIBLE = 0
    INVALID_COUNTRY_CODE = 1
    TOO_SHORT = 2
    TOO_LONG = 3


# Derived data structures
SUPPORTED_REGIONS = set([_item for _sublist in COUNTRY_CODE_TO_REGION_CODE.values() for _item in _sublist])
_NANPA_REGIONS = set(COUNTRY_CODE_TO_REGION_CODE[_NANPA_COUNTRY_CODE])


def _extract_possible_number(number):
    """Attempt to extract a possible number from the string passed in.

    This currently strips all leading characters that cannot be used to
    start a phone number. Characters that can be used to start a phone number
    are defined in the VALID_START_CHAR_PATTERN. If none of these characters
    are found in the number passed in, an empty string is returned. This
    function also attempts to strip off any alternative extensions or endings
    if two or more are present, such as in the case of: (530) 583-6985
    x302/x2303. The second extension here makes this actually two phone
    numbers, (530) 583-6985 x302 and (530) 583-6985 x2303. We remove the
    second extension so that the first number is parsed correctly.

    Arguments:
    number -- The string that might contain a phone number.

    Returns the number, stripped of any non-phone-number prefix (such
    as "Tel:") or an empty string if no character used to start phone
    numbers (such as + or any digit) is found in the number
    """
    match = _VALID_START_CHAR_PATTERN.search(number)
    if match:
        number = number[match.start():]
        # Remove trailing non-alpha non-numberical characters.
        trailing_chars_match = _UNWANTED_END_CHAR_PATTERN.search(number)
        if trailing_chars_match:
            number = number[:trailing_chars_match.start()]
        # Check for extra numbers at the end.
        second_number_match = _SECOND_NUMBER_START_PATTERN.search(number)
        if second_number_match:
            number = number[:second_number_match.start()]
        return number
    else:
        return u""


def _is_viable_phone_number(number):
    """Checks to see if a string could possibly be a phone number.

    At the moment, checks to see that the string begins with at least 3
    digits, ignoring any punctuation commonly found in phone numbers.  This
    method does not require the number to be normalized in advance - but does
    assume that leading non-number symbols have been removed, such as by the
    method _extract_possible_number.

    Arguments:
    number -- string to be checked for viability as a phone number

    Returns True if the number could be a phone number of some sort, otherwise
    False
    """
    if len(number) < _MIN_LENGTH_FOR_NSN:
        return False
    match = fullmatch(_VALID_PHONE_NUMBER_PATTERN, number)
    return bool(match)


def _normalize(number):
    """Normalizes a string of characters representing a phone number.

    This performs the following conversions:

     - Wide-ascii digits are converted to normal ASCII (European) digits.
     - Letters are converted to their numeric representation on a telephone
       keypad. The keypad used here is the one defined in ITU Recommendation
       E.161. This is only done if there are 3 or more letters in the number,
       to lessen the risk that such letters are typos - otherwise alpha
       characters are stripped.
      - Punctuation is stripped.
      - Arabic-Indic numerals are converted to European numerals.

    Arguments:
    number -- string representing a phone number

    Returns the normalized string version of the phone number.
    """
    m = fullmatch(_VALID_ALPHA_PHONE_PATTERN, number)
    if m:
        return _normalize_helper(number, _ALL_NORMALIZATION_MAPPINGS, True)
    else:
        return _normalize_helper(number, _DIGIT_MAPPINGS, True)


def normalize_digits_only(number):
    """Normalizes a string of characters representing a phone number.

    This converts wide-ascii and arabic-indic numerals to European numerals,
    and strips punctuation and alpha characters.

    Arguments:
    number -- a string representing a phone number

    Returns the normalized string version of the phone number.
    """
    return _normalize_helper(number, _DIGIT_MAPPINGS, True)


def convert_alpha_characters_in_number(number):
    """Convert alpha chars in a number to their respective digits on a keypad.

    Retains existing formatting. This implementation of this function also
    converts wide-Unicode digits to normal ASCII digits, and converts
    Arabic-Indic numerals to European numerals.
    """
    return _normalize_helper(number, _ALL_NORMALIZATION_MAPPINGS, False)


def length_of_geographical_area_code(numobj):
    """Return length of the geographical area code for a number.

    Gets the length of the geographical area code in the national_number
    field of the PhoneNumber object passed in, so that clients could use it to
    split a national significant number into geographical area code and
    subscriber number. It works in such a way that the resultant subscriber
    number should be diallable, at least on some devices. An example of how
    this could be used:

    >>> import phonenumbers
    >>> numobj = phonenumbers.parse("16502530000", "US")
    >>> nsn = phonenumbers.national_significant_number(numobj)
    >>> ac_len = phonenumbers.length_of_geographical_area_code(numobj)
    >>> if ac_len > 0:
    ...     area_code = nsn[:ac_len]
    ...     subscriber_number = nsn[ac_len:]
    ... else:
    ...     area_code = ""
    ...     subscriber_number = nsn

    N.B.: area code is a very ambiguous concept, so the I18N team generally
    recommends against using it for most purposes. Read the following
    carefully before deciding to use this method:

     - geographical area codes change over time, and this method honors those
       changes; therefore, it doesn't guarantee the stability of the result it
       produces.
     - subscriber numbers may not be diallable from all devices (notably
       mobile devices, which typically requires the full national_number to be
       dialled in most countries).

     - most non-geographical numbers have no area codes.
     - some geographical numbers have no area codes.

    Arguments:
    numobj -- The PhoneNumber object to find the length of the area code form.

    Returns the length of area code of the PhoneNumber object passed in.
    """
    region_code = region_code_for_number(numobj)
    if not _is_valid_region_code(region_code):
        return 0
    metadata = PhoneMetadata.region_metadata[region_code]
    if metadata.national_prefix is None:
        return 0
    pn_type = _number_type_helper(national_significant_number(numobj),
                                  metadata)

    # Most numbers other than the two types below have to be dialled in full.
    if (pn_type != PhoneNumberType.FIXED_LINE and
        pn_type != PhoneNumberType.FIXED_LINE_OR_MOBILE):
        return 0

    return length_of_national_destination_code(numobj)


def length_of_national_destination_code(numobj):
    """Return length of the national destination code code for a number.

    Gets the length of the national destination code (NDC) from the
    PhoneNumber object passed in, so that clients could use it to split a
    national significant number into NDC and subscriber number. The NDC of a
    phone number is normally the first group of digit(s) right after the
    country calling code when the number is formatted in the international
    format, if there is a subscriber number part that follows. An example of
    how this could be used:

    >>> import phonenumbers
    >>> numobj = phonenumbers.parse("18002530000", "US")
    >>> nsn = phonenumbers.national_significant_number(numobj)
    >>> ndc_len = phonenumbers.length_of_national_destination_code(numobj)
    >>> if ndc_len > 0:
    ...     national_destination_code = nsn[:ndc_len]
    ...     subscriber_number = nsn[ndc_len:]
    ... else:
    ...     national_destination_code = ""
    ...     subscriber_number = nsn

    Refer to the unittests to see the difference between this function and
    length_of_geographical_area_code().

    Arguments:
    numobj -- The PhoneNumber object to find the length of the NDC from.

    Returns the length of NDC of the PhoneNumber object passed in.
    """
    if numobj.extension is not None:
        # We don't want to alter the object given to us, but we don't want to
        # include the extension when we format it, so we copy it and clear the
        # extension here.
        copied_numobj = PhoneNumber()
        copied_numobj.merge_from(numobj)
        copied_numobj.extension = None
    else:
        copied_numobj = numobj

    nsn = format_number(copied_numobj, PhoneNumberFormat.INTERNATIONAL)
    number_groups = re.split(_NON_DIGITS_PATTERN, nsn)

    # The pattern will start with "+COUNTRY_CODE " so the first group will
    # always be the empty string (before the + symbol) and the second group
    # will be the country calling code. The third group will be area code if
    # it is not the last group.
    if len(number_groups) <= 3:
        return 0

    if (region_code_for_number(numobj) == "AR" and
        number_type(numobj) == PhoneNumberType.MOBILE):
        # Argentinian mobile numbers, when formatted in the international
        # format, are in the form of +54 9 NDC XXXX... As a result, we take the
        # length of the third group (NDC) and add 1 for the digit 9, which also
        # forms part of the national significant number.
        #
        # TODO: Investigate the possibility of better modeling the metadata to
        # make it easier to obtain the NDC.
        return len(number_groups[3]) + 1
    return len(number_groups[2])


def _normalize_helper(number, replacements, remove_non_matches):
    """Normalizes a string of characters representing a phone number by
    replacing all characters found in the accompanying map with the values
    therein, and stripping all other characters if remove_non_matches is true.

    Arguments:
    number -- a string representing a phone number
    replacements -- a mapping of characters to what they should be replaced
              by in the normalized version of the phone number
    remove_non_matches -- indicates whether characters that are not able to be
              replaced should be stripped from the number. If this is False,
              they will be left unchanged in the number.

    Returns the normalized string version of the phone number.
    """
    normalized_number = []
    for char in number:
        new_digit = replacements.get(char.upper(), None)
        if new_digit is not None:
            normalized_number.append(new_digit)
        elif not remove_non_matches:
            normalized_number.append(char)
        # If neither of the above are true, we remove this character
    return u''.join(normalized_number)


def _is_valid_region_code(region_code):
    """Helper function to check region code is not unknown or None"""
    if region_code is None:
        return False
    return (region_code.upper() in SUPPORTED_REGIONS)


def format_number(numobj, num_format):
    """Formats a phone number in the specified format using default rules.

    Note that this does not promise to produce a phone number that the user
    can dial from where they are - although we do format in either 'national'
    or 'international' format depending on what the client asks for, we do not
    currently support a more abbreviated format, such as for users in the same
    "area" who could potentially dial the number without area code. Note that
    if the phone number has a country calling code of 0 or an otherwise
    invalid country calling code, we cannot work out which formatting rules to
    apply so we return the national significant number with no formatting
    applied.

    Arguments:
    numobj -- The phone number to be formatted.
    num_format --  The format the phone number should be formatted into

    Returns the formatted phone number.
    """
    country_code = numobj.country_code
    nsn = national_significant_number(numobj)
    if num_format == PhoneNumberFormat.E164:
        # Early exit for E164 case since no formatting of the national number needs to be applied.
        # Extensions are not formatted.
        return _format_number_by_format(country_code, num_format, nsn)

    # Note region_code_for_country_code() is used because formatting
    # information for regions which share a country calling code is contained
    # by only one region for performance reasons. For example, for NANPA
    # regions it will be contained in the metadata for US.
    region_code = region_code_for_country_code(country_code)
    if not _is_valid_region_code(region_code):
        return nsn

    formatted_number = _format_national_number(nsn, region_code, num_format)
    formatted_number = _maybe_get_formatted_extension(numobj,
                                                      region_code,
                                                      num_format,
                                                      formatted_number)
    return _format_number_by_format(country_code,
                                    num_format,
                                    formatted_number)


def format_by_pattern(numobj, num_format, user_defined_formats):
    """Formats a phone number using client-defined formatting rules."

    Note that if the phone number has a country calling code of zero or an
    otherwise invalid country calling code, we cannot work out things like
    whether there should be a national prefix applied, or how to format
    extensions, so we return the national significant number with no
    formatting applied.

    Arguments:
    numobj -- The phone number to be formatted
    num_format -- The format the phone number should be formatted into
    user_defined_formats -- formatting rules specified by clients

    Returns the formatted phone number.
    """
    country_code = numobj.country_code
    nsn = national_significant_number(numobj)
    # Note region_code_for_country_code() is used because formatting
    # information for regions which share a country calling code is contained
    # by only one region for performance reasons. For example, for NANPA
    # regions it will be contained in the metadata for US.
    region_code = region_code_for_country_code(country_code)
    if not _is_valid_region_code(region_code):
        return nsn
    user_defined_formats_copy = []
    for this_format in user_defined_formats:
        np_formatting_rule = this_format.national_prefix_formatting_rule
        if (np_formatting_rule is not None and len(np_formatting_rule) > 0):
            # Before we do a replacement of the national prefix pattern $NP
            # with the national prefix, we need to copy the rule so that
            # subsequent replacements for different numbers have the
            # appropriate national prefix.
            this_format_copy = NumberFormat()
            this_format_copy.merge_from(this_format)
            metadata = PhoneMetadata.region_metadata[region_code]
            national_prefix = metadata.national_prefix
            if (national_prefix is not None and len(national_prefix) > 0):
                # Replace $NP with national prefix and $FG with the first
                # group (\1) matcher.
                np_formatting_rule = re.sub(_NP_PATTERN,
                                            national_prefix,
                                            np_formatting_rule,
                                            count=1)
                np_formatting_rule = re.sub(_FG_PATTERN,
                                            u"\\\\1",
                                            np_formatting_rule,
                                            count=1)
                this_format_copy.national_prefix_formatting_rule = np_formatting_rule
            else:
                # We don't want to have a rule for how to format the national
                # prefix if there isn't one.
                this_format_copy.national_prefix_formatting_rule = None
            user_defined_formats_copy.append(this_format_copy)
        else:
            # Otherwise, we just add the original rule to the modified list of
            # formats.
            user_defined_formats_copy.append(this_format)

    formatted_number = _format_according_to_formats(nsn,
                                                    user_defined_formats_copy,
                                                    num_format)
    formatted_number = _maybe_get_formatted_extension(numobj,
                                                      region_code,
                                                      num_format,
                                                      formatted_number)
    formatted_number = _format_number_by_format(country_code,
                                                num_format,
                                                formatted_number)
    return formatted_number


def format_national_number_with_carrier_code(numobj, carrier_code):
    """Format a number in national format for dialing using the specified carrier.

    The carrier-code will always be used regardless of whether the phone
    number already has a preferred domestic carrier code stored. If
    carrier_code contains an empty string, returns the number in national
    format without any carrier code.

    Arguments:
    numobj -- The phone number to be formatted
    carrier_code -- The carrier selection code to be used

    Returns the formatted phone number in national format for dialing using
    the carrier as specified in the carrier_code.
    """
    country_code = numobj.country_code
    nsn = national_significant_number(numobj)
    # Note region_code_for_country_code() is used because formatting
    # information for regions which share a country calling code is contained
    # by only one region for performance reasons. For example, for NANPA
    # regions it will be contained in the metadata for US.
    region_code = region_code_for_country_code(country_code)
    if not _is_valid_region_code(region_code):
        return nsn

    formatted_number = _format_national_number(nsn,
                                               region_code,
                                               PhoneNumberFormat.NATIONAL,
                                               carrier_code)
    formatted_number = _maybe_get_formatted_extension(numobj,
                                                      region_code,
                                                      PhoneNumberFormat.NATIONAL,
                                                      formatted_number)
    formatted_number = _format_number_by_format(country_code,
                                                PhoneNumberFormat.NATIONAL,
                                                formatted_number)
    return formatted_number


def format_national_number_with_preferred_carrier_code(numobj, fallback_carrier_code):
    """Formats a phone number in national format for dialing using the carrier
    as specified in the preferred_domestic_carrier_code field of the
    PhoneNumber object passed in. If that is missing, use the
    fallback_carrier_code passed in instead. If there is no
    preferred_domestic_carrier_code, and the fallback_carrier_code contains an
    empty string, return the number in national format without any carrier
    code.

    Use format_national_number_with_carrier_code instead if the carrier code
    passed in should take precedence over the number's
    preferred_domestic_carrier_code when formatting.

    Arguments:
    numobj -- The phone number to be formatted
    carrier_code -- The carrier selection code to be used, if none is found in the
              phone number itself.

    Returns the formatted phone number in national format for dialing using
    the number's preferred_domestic_carrier_code, or the fallback_carrier_code
    pass in if none is found.
    """
    if numobj.preferred_domestic_carrier_code is not None:
        carrier_code = numobj.preferred_domestic_carrier_code
    else:
        carrier_code = fallback_carrier_code
    return format_national_number_with_carrier_code(numobj, carrier_code)


def format_out_of_country_calling_number(numobj, region_calling_from):
    """Formats a phone number for out-of-country dialing purposes.

    If no region_calling_from is supplied, we format the number in its
    INTERNATIONAL format. If the country calling code is the same as the
    region where the number is from, then NATIONAL formatting will be applied.

    If the number itself has a country calling code of zero or an otherwise
    invalid country calling code, then we return the number with no formatting
    applied.

    Note this function takes care of the case for calling inside of NANPA and
    between Russia and Kazakhstan (who share the same country calling
    code). In those cases, no international prefix is used. For regions which
    have multiple international prefixes, the number in its INTERNATIONAL
    format will be returned instead.

    Arguments:
    numobj -- The phone number to be formatted
    region_calling_from -- The ISO 3166-1 two-letter region code that denotes
              the region where the call is being placed

    Returns the formatted phone number
    """
    if not _is_valid_region_code(region_calling_from):
        return format_number(numobj, PhoneNumberFormat.INTERNATIONAL)
    country_code = numobj.country_code
    region_code = region_code_for_country_code(country_code)
    nsn = national_significant_number(numobj)
    if not _is_valid_region_code(region_code):
        return nsn
    if country_code == _NANPA_COUNTRY_CODE:
        if is_nanpa_country(region_calling_from):
            # For NANPA regions, return the national format for these regions
            # but prefix it with the country calling code.
            return (unicode(country_code) + u" " +
                    format_number(numobj, PhoneNumberFormat.NATIONAL))
    elif country_code == country_code_for_region(region_calling_from):
        # For regions that share a country calling code, the country calling
        # code need not be dialled.  This also applies when dialling within a
        # region, so this if clause covers both these cases.  Technically this
        # is the case for dialling from La Reunion to other overseas
        # departments of France (French Guiana, Martinique, Guadeloupe), but
        # not vice versa - so we don't cover this edge case for now and for
        # those cases return the version including country calling code.
        # Details here:
        # http://www.petitfute.com/voyage/225-info-pratiques-reunion
        return format_number(numobj, PhoneNumberFormat.NATIONAL)

    formatted_national_number = _format_national_number(nsn,
                                                        region_code,
                                                        PhoneNumberFormat.INTERNATIONAL)
    metadata = PhoneMetadata.region_metadata[region_calling_from.upper()]
    international_prefix = metadata.international_prefix

    # For regions that have multiple international prefixes, the international
    # format of the number is returned, unless there is a preferred
    # international prefix.
    i18n_prefix_for_formatting = u""
    i18n_match = fullmatch(_UNIQUE_INTERNATIONAL_PREFIX, international_prefix)
    if i18n_match:
        i18n_prefix_for_formatting = international_prefix
    elif metadata.preferred_international_prefix is not None:
        i18n_prefix_for_formatting = metadata.preferred_international_prefix

    formatted_number = _maybe_get_formatted_extension(numobj,
                                                      region_code,
                                                      PhoneNumberFormat.INTERNATIONAL,
                                                      formatted_national_number)
    if len(i18n_prefix_for_formatting) > 0:
        formatted_number = (i18n_prefix_for_formatting + u" " +
                            unicode(country_code) + u" " + formatted_number)
    else:
        formatted_number = _format_number_by_format(country_code,
                                                    PhoneNumberFormat.INTERNATIONAL,
                                                    formatted_number)
    return formatted_number


def format_in_original_format(numobj, region_calling_from):
    """Format a number using the original format that the number was parsed from.

    The original format is embedded in the country_code_source field of the
    PhoneNumber object passed in. If such information is missing, the number
    will be formatted into the NATIONAL format by default.

    Arguments:
    number -- The phone number that needs to be formatted in its original
              number format
    region_calling_from -- The region whose IDD needs to be prefixed if the
              original number has one.

    Returns the formatted phone number in its original number format.
    """
    if numobj.country_code_source is None:
        return format_number(numobj, PhoneNumberFormat.NATIONAL)

    if (numobj.country_code_source ==
        CountryCodeSource.FROM_NUMBER_WITH_PLUS_SIGN):
        return format_number(numobj, PhoneNumberFormat.INTERNATIONAL)
    elif numobj.country_code_source == CountryCodeSource.FROM_NUMBER_WITH_IDD:
        return format_out_of_country_calling_number(numobj, region_calling_from)
    elif (numobj.country_code_source ==
          CountryCodeSource.FROM_NUMBER_WITHOUT_PLUS_SIGN):
        return format_number(numobj, PhoneNumberFormat.INTERNATIONAL)[1:]
    else:
        return format_number(numobj, PhoneNumberFormat.NATIONAL)


def format_out_of_country_keeping_alpha_chars(numobj, region_calling_from):
    """Formats a phone number for out-of-country dialing purposes.

    Note that in this version, if the number was entered originally using
    alpha characters and this version of the number is stored in raw_input,
    this representation of the number will be used rather than the digit
    representation. Grouping information, as specified by characters such as
    "-" and " ", will be retained.

    Caveats:

     - This will not produce good results if the country calling code is both
       present in the raw input _and_ is the start of the national
       number. This is not a problem in the regions which typically use alpha
       numbers.

     - This will also not produce good results if the raw input has any
       grouping information within the first three digits of the national
       number, and if the function needs to strip preceding digits/words in
       the raw input before these digits. Normally people group the first
       three digits together so this is not a huge problem - and will be fixed
       if it proves to be so.

    Arguments:
    numobj -- The phone number that needs to be formatted.
    region_calling_from -- The region where the call is being placed.

    Returns the formatted phone number
    """
    raw_input = numobj.raw_input
    # If there is no raw input, then we can't keep alpha characters because there aren't any.
    # In this case, we return format_out_of_country_calling_number.
    if raw_input is None or len(raw_input) == 0:
        return format_out_of_country_calling_number(numobj, region_calling_from)
    country_code = numobj.country_code
    region_code = region_code_for_country_code(country_code)
    if not _is_valid_region_code(region_code):
        return raw_input
    # Strip any prefix such as country calling code, IDD, that was present. We
    # do this by comparing the number in raw_input with the parsed number.  To
    # do this, first we normalize punctuation. We retain number grouping
    # symbols such as " " only.
    raw_input = _normalize_helper(raw_input,
                                  _ALL_PLUS_NUMBER_GROUPING_SYMBOLS,
                                  True)
    # Now we trim everything before the first three digits in the parsed
    # number. We choose three because all valid alpha numbers have 3 digits at
    # the start - if it does not, then we don't trim anything at
    # all. Similarly, if the national number was less than three digits, we
    # don't trim anything at all.
    national_number = national_significant_number(numobj)
    if len(national_number) > 3:
        first_national_number_digit = raw_input.find(national_number[:3])
        if first_national_number_digit != -1:
            raw_input = raw_input[first_national_number_digit:]

    metadata = PhoneMetadata.region_metadata.get(region_calling_from.upper(), None)
    if country_code == _NANPA_COUNTRY_CODE:
        if is_nanpa_country(region_calling_from):
            return unicode(country_code) + u" " + raw_input
    elif country_code == country_code_for_region(region_calling_from):
        # Here we copy the formatting rules so we can modify the pattern we
        # expect to match against.
        available_formats = []
        for this_format in metadata.number_format:
            new_format = NumberFormat()
            new_format.merge_from(this_format)
            # The first group is the first group of digits that the user
            # determined.
            new_format.pattern = u"(\\d+)(.*)"
            # Here we just concatenate them back together after the national
            # prefix has been fixed.
            new_format.format = ur"\1\2"
            available_formats.append(new_format)

        # Now we format using these patterns instead of the default pattern,
        # but with the national prefix prefixed if necessary, by choosing the
        # format rule based on the leading digits present in the unformatted
        # national number.  This will not work in the cases where the pattern
        # (and not the leading digits) decide whether a national prefix needs
        # to be used, since we have overridden the pattern to match anything,
        # but that is not the case in the metadata to date.
        return _format_according_to_formats(raw_input,
                                            available_formats,
                                            PhoneNumberFormat.NATIONAL)
    international_prefix = metadata.international_prefix
    # For countries that have multiple international prefixes, the
    # international format of the number is returned, unless there is a
    # preferred international prefix.
    i18n_match = fullmatch(_UNIQUE_INTERNATIONAL_PREFIX, international_prefix)
    if i18n_match:
        i18n_prefix_for_formatting = international_prefix
    else:
        i18n_prefix_for_formatting = metadata.preferred_international_prefix
    formatted_number = _maybe_get_formatted_extension(numobj,
                                                      region_code,
                                                      PhoneNumberFormat.INTERNATIONAL,
                                                      raw_input)
    if i18n_prefix_for_formatting and len(i18n_prefix_for_formatting) > 0:
        formatted_number = (i18n_prefix_for_formatting + u" " +
                            unicode(country_code) + u" " + formatted_number)
    else:
        formatted_number = _format_number_by_format(country_code,
                                                    PhoneNumberFormat.INTERNATIONAL,
                                                    formatted_number)
    return formatted_number


def national_significant_number(numobj):
    """Gets the national significant number of a phone number.

    Note that a national significant number doesn't contain a national prefix
    or any formatting.

    Arguments:
    numobj -- The PhoneNumber object for which the national significant number
              is needed.

    Returns the national significant number of the PhoneNumber object passed
    in.
    """
    # The leading zero in the national (significant) number of an Italian
    # phone number has a special meaning. Unlike the rest of the world, it
    # indicates the number is a landline number. There have been plans to
    # migrate landline numbers to start with the digit two since December
    # 2000, but it has not yet happened.  See
    # http://en.wikipedia.org/wiki/%2B39 for more details.  Other regions such
    # as Cote d'Ivoire and Gabon use this for their mobile numbers.

    national_number = u""
    if (numobj.italian_leading_zero is not None and
        numobj.italian_leading_zero and
        _is_leading_zero_possible(numobj.country_code)):
        national_number = u"0"
    national_number += str(numobj.national_number)
    return national_number


def _format_number_by_format(country_code, num_format, formatted_number):
    """A helper function that is used by format_number and format_by_pattern."""
    if num_format == PhoneNumberFormat.E164:
        return _PLUS_SIGN + unicode(country_code) + formatted_number
    elif num_format == PhoneNumberFormat.INTERNATIONAL:
        return _PLUS_SIGN + unicode(country_code) + u" " + formatted_number
    elif num_format == PhoneNumberFormat.RFC3966:
        return _PLUS_SIGN + unicode(country_code) + u"-" + formatted_number
    else:
        return formatted_number


def _format_national_number(number, region_code, num_format, carrier_code=None):
    """Format a national number."""
    # Note in some regions, the national number can be written in two
    # completely different ways depending on whether it forms part of the
    # NATIONAL format or INTERNATIONAL format. The num_format parameter here
    # is used to specify which format to use for those cases. If a carrier_code
    # is specified, this will be inserted into the formatted string to replace
    # $CC.
    metadata = PhoneMetadata.region_metadata.get(region_code.upper(), None)
    intl_number_formats = metadata.intl_number_format

    # When the intl_number_formats exists, we use that to format national
    # number for the INTERNATIONAL format instead of using the
    # number_desc.number_formats.
    if (len(intl_number_formats) == 0 or
        num_format == PhoneNumberFormat.NATIONAL):
        available_formats = metadata.number_format
    else:
        available_formats = metadata.intl_number_format

    formatted_national_number = _format_according_to_formats(number,
                                                             available_formats,
                                                             num_format,
                                                             carrier_code)
    if num_format == PhoneNumberFormat.RFC3966:
        formatted_national_number = re.sub(_SEPARATOR_PATTERN, u"-",
                                           formatted_national_number)
    return formatted_national_number


def _format_according_to_formats(number, available_formats, num_format,
                                 carrier_code=None):
    """ """
    # Note that carrier_code is optional - if None or an empty string, no
    # carrier code replacement will take place.
    for this_format in available_formats:
        size = len(this_format.leading_digits_pattern)
        # We always use the last leading_digits_pattern, as it is the most detailed.
        if size > 0:
            ld_pattern = re.compile(this_format.leading_digits_pattern[-1])
            ld_match = ld_pattern.match(number)
        if size == 0 or ld_match:
            format_pattern = re.compile(this_format.pattern)
            format_match = fullmatch(format_pattern, number)
            if format_match:
                number_format_rule = this_format.format
                if (num_format == PhoneNumberFormat.NATIONAL and
                    carrier_code is not None and len(carrier_code) > 0 and
                    this_format.domestic_carrier_code_formatting_rule is not None and
                    len(this_format.domestic_carrier_code_formatting_rule) > 0):
                    # Replace the $CC in the formatting rule with the desired
                    # carrier code.
                    cc_format_rule = this_format.domestic_carrier_code_formatting_rule
                    cc_format_rule = re.sub(_CC_PATTERN,
                                            carrier_code,
                                            cc_format_rule,
                                            count=1)

                    # Now replace the $FG in the formatting rule with the
                    # first group and the carrier code combined in the
                    # appropriate way.
                    number_format_rule = re.sub(_FIRST_GROUP_PATTERN,
                                                cc_format_rule,
                                                number_format_rule,
                                                count=1)
                    return re.sub(format_pattern, number_format_rule, number)
                else:
                    # Use the national prefix formatting rule instead.
                    national_prefix_formatting_rule = this_format.national_prefix_formatting_rule
                    if (num_format == PhoneNumberFormat.NATIONAL and
                        national_prefix_formatting_rule is not None and
                        len(national_prefix_formatting_rule) > 0):
                        first_group_rule = re.sub(_FIRST_GROUP_PATTERN,
                                                  national_prefix_formatting_rule,
                                                  number_format_rule,
                                                  count=1)
                        return re.sub(format_pattern, first_group_rule, number)
                    else:
                        return re.sub(format_pattern, number_format_rule, number)

    # If no pattern above is matched, we format the number as a whole.
    return number


def example_number(region_code):
    """Gets a valid number for the specified region.

    Arguments:
    region_code -- The ISO 3166-1 two-letter region code that denotes
              the region for which an example number is needed.

    Returns a valid fixed-line number for the specified region. Returns None
    when the metadata does not contain such information.
    """
    return example_number_for_type(region_code, PhoneNumberType.FIXED_LINE)


def example_number_for_type(region_code, num_type):
    """Gets a valid number for the specified region and number type.

    Arguments:
    region_code -- The ISO 3166-1 two-letter region code that denotes
              the region for which an example number is needed.
    num_type -- The type of number that is needed.

    Returns a valid number for the specified region and type. Returns None
    when the metadata does not contain such information.
    """
    # Check the region code is valid.
    if not _is_valid_region_code(region_code):
        return None
    metadata = PhoneMetadata.region_metadata[region_code.upper()]
    desc = _number_desc_for_type(metadata, num_type)
    if desc.example_number is not None:
        try:
            return parse(desc.example_number, region_code)
        except NumberParseException:
            pass
    return None


def _maybe_get_formatted_extension(numobj, region_code, num_format, number):
    """Appends the formatted extension of a phone number to formatted number,
    if the phone number had an extension specified.
    """
    if (numobj.extension is not None and len(numobj.extension) > 0):
        if num_format == PhoneNumberFormat.RFC3966:
            return number + _RFC3966_EXTN_PREFIX + numobj.extension
        else:
            return _format_extension(numobj.extension, region_code, number)
    return number


def _format_extension(extension, region_code, number):
    """Formats the extension part of the phone number by prefixing it with the
    appropriate extension prefix. This will be the default extension prefix,
    unless overridden by a preferred extension prefix for this region.
    """
    metadata = PhoneMetadata.region_metadata[region_code.upper()]
    if metadata.preferred_extn_prefix is not None:
        return number + metadata.preferred_extn_prefix + extension
    else:
        return number + _DEFAULT_EXTN_PREFIX + extension


def _number_desc_for_type(metadata, num_type):
    """Return the PhoneNumberDesc of the metadata for the given number type"""
    if num_type == PhoneNumberType.PREMIUM_RATE:
        return metadata.premium_rate
    elif num_type == PhoneNumberType.TOLL_FREE:
        return metadata.toll_free
    elif num_type == PhoneNumberType.MOBILE:
        return metadata.mobile
    elif (num_type == PhoneNumberType.FIXED_LINE or
          num_type == PhoneNumberType.FIXED_LINE_OR_MOBILE):
        return metadata.fixed_line
    elif num_type == PhoneNumberType.SHARED_COST:
        return metadata.shared_cost
    elif num_type == PhoneNumberType.VOIP:
        return metadata.voip
    elif num_type == PhoneNumberType.PERSONAL_NUMBER:
        return metadata.personal_number
    elif num_type == PhoneNumberType.PAGER:
        return metadata.pager
    elif num_type == PhoneNumberType.UAN:
        return metadata.uan
    else:
        return metadata.general_desc


def number_type(numobj):
    """Gets the type of a phone number.

    Arguments:
    numobj -- The PhoneNumber object that we want to know the type of.

    Returns the type of the phone number.
    """
    region_code = region_code_for_number(numobj)
    if not _is_valid_region_code(region_code):
        return PhoneNumberType.UNKNOWN
    national_number = national_significant_number(numobj)
    return _number_type_helper(national_number,
                               PhoneMetadata.region_metadata[region_code])


def _number_type_helper(national_number, metadata):
    """Return the type of the given number against the metadata"""
    general_desc = metadata.general_desc
    if (general_desc.national_number_pattern is None or
        not _is_number_matching_desc(national_number, general_desc)):
        return PhoneNumberType.UNKNOWN
    if _is_number_matching_desc(national_number, metadata.premium_rate):
        return PhoneNumberType.PREMIUM_RATE
    if _is_number_matching_desc(national_number, metadata.toll_free):
        return PhoneNumberType.TOLL_FREE
    if _is_number_matching_desc(national_number, metadata.shared_cost):
        return PhoneNumberType.SHARED_COST
    if _is_number_matching_desc(national_number, metadata.voip):
        return PhoneNumberType.VOIP
    if _is_number_matching_desc(national_number, metadata.personal_number):
        return PhoneNumberType.PERSONAL_NUMBER
    if _is_number_matching_desc(national_number, metadata.pager):
        return PhoneNumberType.PAGER
    if _is_number_matching_desc(national_number, metadata.uan):
        return PhoneNumberType.UAN

    if _is_number_matching_desc(national_number, metadata.fixed_line):
        if metadata.same_mobile_and_fixed_line_pattern:
            return PhoneNumberType.FIXED_LINE_OR_MOBILE
        elif _is_number_matching_desc(national_number, metadata.mobile):
            return PhoneNumberType.FIXED_LINE_OR_MOBILE
        return PhoneNumberType.FIXED_LINE

    # Otherwise, test to see if the number is mobile. Only do this if certain
    # that the patterns for mobile and fixed line aren't the same.
    if (not metadata.same_mobile_and_fixed_line_pattern and
        _is_number_matching_desc(national_number, metadata.mobile)):
        return PhoneNumberType.MOBILE
    return PhoneNumberType.UNKNOWN


def _is_number_matching_desc(national_number, number_desc):
    """Determine if the number matches the given PhoneNumberDesc"""
    if number_desc is None:
        return False
    possible_re = re.compile(number_desc.possible_number_pattern or "")
    national_re = re.compile(number_desc.national_number_pattern or "")
    return (fullmatch(possible_re, national_number) and
            fullmatch(national_re, national_number))


def is_valid_number(numobj):
    """Tests whether a phone number matches a valid pattern.

    Note this doesn't verify the number is actually in use, which is
    impossible to tell by just looking at a number itself.

    Arguments:
    numobj -- The phone number object that we want to validate

    Returns a boolean that indicates whether the number is of a valid pattern.
    """
    region_code = region_code_for_number(numobj)
    return (_is_valid_region_code(region_code) and
            is_valid_number_for_region(numobj, region_code))


def is_valid_number_for_region(numobj, region_code):
    """Tests whether a phone number is valid for a certain region.

    Note this doesn't verify the number is actually in use, which is
    impossible to tell by just looking at a number itself. If the country
    calling code is not the same as the country calling code for the region,
    this immediately exits with false. After this, the specific number pattern
    rules for the region are examined. This is useful for determining for
    example whether a particular number is valid for Canada, rather than just
    a valid NANPA number.

    Arguments:
    numobj -- The phone number object that we want to validate.
    region_code -- The ISO 3166-1 two-letter region code that denotes the
              region that we want to validate the phone number for.

    Returns a boolean that indicates whether the number is of a valid pattern.
    """
    if numobj.country_code != country_code_for_region(region_code):
        return False
    metadata = PhoneMetadata.region_metadata[region_code.upper()]
    general_desc = metadata.general_desc
    nsn = national_significant_number(numobj)

    # For regions where we don't have metadata for PhoneNumberDesc, we treat
    # any number passed in as a valid number if its national significant
    # number is between the minimum and maximum lengths defined by ITU for a
    # national significant number.
    if general_desc.national_number_pattern is None:
        num_len = len(nsn)
        return (num_len > _MIN_LENGTH_FOR_NSN and num_len < _MAX_LENGTH_FOR_NSN)
    return (_number_type_helper(nsn, metadata) != PhoneNumberType.UNKNOWN)


def region_code_for_number(numobj):
    """Returns the region where a phone number is from.

    This could be used for geocoding at the region level.

    Arguments:
    numobj -- The phone number object whose origin we want to know

    Returns the region where the phone number is from, or None if no region
    matches this calling code.
    """
    country_code = numobj.country_code
    regions = COUNTRY_CODE_TO_REGION_CODE.get(country_code, None)
    if regions is None:
        return None

    if len(regions) == 1:
        return regions[0]
    else:
        return _region_code_for_number_from_list(numobj, regions)


def _region_code_for_number_from_list(numobj, regions):
    """Find the region in a list that matches a number"""
    national_number = national_significant_number(numobj)
    for region_code in regions:
        # If leading_digits is present, use this. Otherwise, do full
        # validation.
        if region_code.upper() not in PhoneMetadata.region_metadata:
            continue
        metadata = PhoneMetadata.region_metadata[region_code.upper()]
        if metadata.leading_digits is not None:
            leading_digit_re = re.compile(metadata.leading_digits)
            match = leading_digit_re.match(national_number)
            if match:
                return region_code
        elif _number_type_helper(national_number, metadata) != PhoneNumberType.UNKNOWN:
            return region_code
    return None


def region_code_for_country_code(country_code):
    """Returns the region code matching a country calling code.

    In the case of no region code being found, UNKNOWN_REGION ('ZZ') will be
    returned. In the case of multiple regions, the one designated in the
    metadata as the "main" region for this calling code will be returned.
    """
    regions = COUNTRY_CODE_TO_REGION_CODE.get(country_code, None)
    if regions is None:
        return UNKNOWN_REGION
    else:
        return regions[0]


def country_code_for_region(region_code):
    """Returns the country calling code for a specific region.

    For example, this would be 1 for the United States, and 64 for New
    Zealand.

    Arguments:
    region_code -- The ISO 3166-1 two-letter region code that denotes
              the region that we want to get the country calling code for.

    Returns the country calling code for the region denoted by region_code.
    """
    if not _is_valid_region_code(region_code):
        return 0
    metadata = PhoneMetadata.region_metadata.get(region_code.upper(), None)
    return metadata.country_code


def ndd_prefix_for_region(region_code, strip_non_digits):
    """Returns the national dialling prefix for a specific region.

    For example, this would be 1 for the United States, and 0 for New
    Zealand. Set strip_non_digits to True to strip symbols like "~" (which
    indicates a wait for a dialling tone) from the prefix returned. If no
    national prefix is present, we return None.

    Warning: Do not use this method for do-your-own formatting - for some
    regions, the national dialling prefix is used only for certain types of
    numbers. Use the library's formatting functions to prefix the national
    prefix when required.

    Arguments:
    region_code -- The ISO 3166-1 two-letter region code that denotes
              the region that we want to get the dialling prefix for.
    strip_non_digits -- whether to strip non-digits from the national
               dialling prefix.

    Returns the dialling prefix for the region denoted by region_code.
    """
    if not _is_valid_region_code(region_code):
        return None
    metadata = PhoneMetadata.region_metadata.get(region_code.upper(), None)
    national_prefix = metadata.national_prefix
    if national_prefix is None or len(national_prefix) == 0:
        return None
    if strip_non_digits:
        # Note: if any other non-numeric symbols are ever used in national
        # prefixes, these would have to be removed here as well.
        national_prefix = re.sub(u"~", u"", national_prefix)
    return national_prefix


def is_nanpa_country(region_code):
    """Checks if this region is a NANPA region.

    Returns True if region_code is one of the regions under the North American
    Numbering Plan Administration (NANPA).
    """
    return (region_code is not None and
            region_code.upper() in _NANPA_REGIONS)


def _is_leading_zero_possible(country_code):
    """Checks whether country_code represents the country calling code from a
    region whose national significant number could contain a leading zero. An
    example of such a region is Italy.  Returns False if no metadata for the
    country is found."""
    region_code = region_code_for_country_code(country_code)
    metadata = PhoneMetadata.region_metadata.get(region_code, None)
    if metadata is None:
        return False
    return metadata.leading_zero_possible


def is_alpha_number(number):
    """Checks if the number is a valid vanity (alpha) number such as 800
    MICROSOFT. A valid vanity number will start with at least 3 digits and
    will have three or more alpha characters. This does not do region-specific
    checks - to work out if this number is actually valid for a region, it
    should be parsed and methods such as is_possible_number_with_reason() and
    is_valid_number() should be used.

    Arguments:
    number -- the number that needs to be checked

    Returns True if the number is a valid vanity number
    """
    if not _is_viable_phone_number(number):
        # Number is too short, or doesn't match the basic phone number pattern.
        return False
    extension, stripped_number = _maybe_strip_extension(number)
    return bool(fullmatch(_VALID_ALPHA_PHONE_PATTERN, stripped_number))


def is_possible_number(numobj):
    """Convenience wrapper around is_possible_number_with_reason.

    Instead of returning the reason for failure, this method returns a boolean
    value.

    Arguments:
    numobj -- the number object that needs to be checked

    Returns True if the number is possible
    """
    return is_possible_number_with_reason(numobj) == ValidationResult.IS_POSSIBLE


def _test_number_length_against_pattern(possible_re, national_number):
    """Helper method to check a number against a particular pattern and
    determine whether it matches, or is too short or too long. Currently, if a
    number pattern suggests that numbers of length 7 and 10 are possible, and
    a number in between these possible lengths is entered, such as of length
    8, this will return TOO_LONG.
    """
    match = fullmatch(possible_re, national_number)
    if match:
        return ValidationResult.IS_POSSIBLE
    search = possible_re.match(national_number)
    if search:
        return ValidationResult.TOO_LONG
    else:
        return ValidationResult.TOO_SHORT


def is_possible_number_with_reason(numobj):
    """Check whether a phone number is a possible number.

    It provides a more lenient check than is_valid_number() in the following
    sense:

     - It only checks the length of phone numbers. In particular, it doesn't
       check starting digits of the number.

     - It doesn't attempt to figure out the type of the number, but uses
       general rules which applies to all types of phone numbers in a
       region. Therefore, it is much faster than is_valid_number.

     - For fixed line numbers, many regions have the concept of area code,
       which together with subscriber number constitute the national
       significant number. It is sometimes okay to dial the subscriber number
       only when dialing in the same area. This function will return true if
       the subscriber-number-only version is passed in. On the other hand,
       because is_valid_number validates using information on both starting
       digits (for fixed line numbers, that would most likely be area codes)
       and length (obviously includes the length of area codes for fixed line
       numbers), it will return false for the subscriber-number-only version.

    Arguments:
    numobj -- The number object that needs to be checked

    Returns a value from ValidationResult which indicates whether the number
    is possible
    """
    national_number = national_significant_number(numobj)
    country_code = numobj.country_code
    # Note: For Russian Fed and NANPA numbers, we just use the rules from the
    # default region (US or Russia) since the region_code_for_number() will
    # not work if the number is possible but not valid. This would need to be
    # revisited if the possible number pattern ever differed between various
    # regions within those plans.
    region_code = region_code_for_country_code(country_code)
    if not _is_valid_region_code(region_code):
        return ValidationResult.INVALID_COUNTRY_CODE

    metadata = PhoneMetadata.region_metadata.get(region_code, None)
    general_desc = metadata.general_desc

    # Handling case of numbers with no metadata.
    if general_desc.national_number_pattern is None:
        num_len = len(national_number)
        if num_len < _MIN_LENGTH_FOR_NSN:
            return ValidationResult.TOO_SHORT
        elif num_len > _MAX_LENGTH_FOR_NSN:
            return ValidationResult.TOO_LONG
        else:
            return ValidationResult.IS_POSSIBLE
    possible_re = re.compile(general_desc.possible_number_pattern or "")
    return _test_number_length_against_pattern(possible_re, national_number)


def is_possible_number_string(number, region_dialing_from):
    """Check whether a phone number string is a possible number.

    Takes a number in the form of a string, and the region where the number
    could be dialed from. It provides a more lenient check than
    is_valid_number; see is_possible_number_with_reason() for details.

    This method first parses the number, then invokes is_possible_number with
    the resultant PhoneNumber object.

    Arguments:
    number -- The number that needs to be checked, in the form of a string.
    region_dialling_from -- The ISO 3166-1 two-letter region code that denotes
              the region that we are expecting the number to be dialed from.
              Note this is different from the region where the number belongs.
              For example, the number +1 650 253 0000 is a number that belongs
              to US. When written in this form, it can be dialed from any
              region. When it is written as 00 1 650 253 0000, it can be
              dialed from any region which uses an international dialling
              prefix of 00. When it is written as 650 253 0000, it can only be
              dialed from within the US, and when written as 253 0000, it can
              only be dialed from within a smaller area in the US (Mountain
              View, CA, to be more specific).

    Returns True if the number is possible
    """
    try:
        return is_possible_number(parse(number, region_dialing_from))
    except NumberParseException:
        return False


def truncate_too_long_number(numobj):
    """Truncate a number object that is too long.

    Attempts to extract a valid number from a phone number that is too long
    to be valid, and resets the PhoneNumber object passed in to that valid
    version. If no valid number could be extracted, the PhoneNumber object
    passed in will not be modified.

    Arguments:
    numobj -- A PhoneNumber object which contains a number that is too long to
              be valid.

    Returns True if a valid phone number can be successfully extracted.
    """
    if is_valid_number(numobj):
        return True
    numobj_copy = PhoneNumber()
    numobj_copy.merge_from(numobj)
    national_number = numobj.national_number

    while not is_valid_number(numobj_copy):
        # Strip a digit off the RHS
        national_number = national_number / 10
        numobj_copy.national_number = national_number
        validation_result = is_possible_number_with_reason(numobj_copy)
        if (validation_result == ValidationResult.TOO_SHORT or
            national_number == 0):
            return False
    # To reach here, numobj_copy is a valid number.  Modify the original object
    numobj.national_number = national_number
    return True


def _extract_country_code(number):
    """Extracts country calling code from number.

    Returns a 2-tuple of (country_calling_code, rest_of_number).  It assumes
    that the leading plus sign or IDD has already been removed.  Returns (0,
    number) if number doesn't start with a valid country calling code.
    """
    for ii in xrange(1, min(len(number), _MAX_LENGTH_COUNTRY_CODE) + 1):
        try:
            country_code = int(number[:ii])
            if country_code in COUNTRY_CODE_TO_REGION_CODE:
                return (country_code, number[ii:])
        except Exception:
            pass
    return (0, number)


def _maybe_extract_country_code(number, metadata, keep_raw_input, numobj):
    """Tries to extract a country calling code from a number.

    This method will return zero if no country calling code is considered to
    be present. Country calling codes are extracted in the following ways:

     - by stripping the international dialing prefix of the region the person
       is dialing from, if this is present in the number, and looking at the
       next digits

     - by stripping the '+' sign if present and then looking at the next
       digits

     - by comparing the start of the number and the country calling code of
       the default region.  If the number is not considered possible for the
       numbering plan of the default region initially, but starts with the
       country calling code of this region, validation will be reattempted
       after stripping this country calling code. If this number is considered
       a possible number, then the first digits will be considered the country
       calling code and removed as such.

    It will raise a NumberParseException if the number starts with a '+' but
    the country calling code supplied after this does not match that of any
    known region.

    Arguments:
    number -- non-normalized telephone number that we wish to extract a
              country calling code from; may begin with '+'
    metadata -- metadata about the region this number may be from, or None
    keep_raw_input -- True if the country_code_source and
              preferred_carrier_code fields of numobj should be populated.
    numobj -- The PhoneNumber object where the country_code and
              country_code_source need to be populated. Note the country_code
              is always populated, whereas country_code_source is only
              populated when keep_raw_input is True.

    Returns a 2-tuple containing:
      - the country calling code extracted or 0 if none could be extracted
      - a string holding the national significant number, in the case
        that a country calling code was extracted. If no country calling code
        was extracted, this will be empty.
    """
    if len(number) == 0:
        return (0, u"")
    full_number = number
    # Set the default prefix to be something that will never match.
    possible_country_idd_prefix = u"NonMatch"
    if metadata is not None:
        possible_country_idd_prefix = metadata.international_prefix

    country_code_source, full_number = _maybe_strip_i18n_prefix_and_normalize(full_number,
                                                                              possible_country_idd_prefix)
    if keep_raw_input:
        numobj.country_code_source = country_code_source

    if country_code_source != CountryCodeSource.FROM_DEFAULT_COUNTRY:
        if len(full_number) < _MIN_LENGTH_FOR_NSN:
            raise NumberParseException(NumberParseException.TOO_SHORT_AFTER_IDD,
                                       "Phone number had an IDD, but after this was not " +
                                       "long enough to be a viable phone number.")
        potential_country_code, rest_of_number = _extract_country_code(full_number)
        if potential_country_code != 0:
            numobj.country_code = potential_country_code
            return (potential_country_code, rest_of_number)

        # If this fails, they must be using a strange country calling code
        # that we don't recognize, or that doesn't exist.
        raise NumberParseException(NumberParseException.INVALID_COUNTRY_CODE,
                                   "Country calling code supplied was not recognised.")
    elif metadata is not None:
        # Check to see if the number starts with the country calling code for
        # the default region. If so, we remove the country calling code, and
        # do some checks on the validity of the number before and after.
        default_country_code = metadata.country_code
        default_country_code_str = str(metadata.country_code)
        normalized_number = full_number
        if normalized_number.startswith(default_country_code_str):
            potential_national_number = full_number[len(default_country_code_str):]
            general_desc = metadata.general_desc
            valid_pattern = re.compile(general_desc.national_number_pattern or "")
            _, potential_national_number = _maybe_strip_national_prefix_carrier_code(potential_national_number,
                                                                                     metadata)
            possible_pattern = re.compile(general_desc.possible_number_pattern or "")

            # If the number was not valid before but is valid now, or if it
            # was too long before, we consider the number with the country
            # calling code stripped to be a better result and keep that
            # instead.
            if ((fullmatch(valid_pattern, full_number) is None and
                 fullmatch(valid_pattern, potential_national_number)) or
                (_test_number_length_against_pattern(possible_pattern, full_number) ==
                 ValidationResult.TOO_LONG)):
                if keep_raw_input:
                    numobj.country_code_source = CountryCodeSource.FROM_NUMBER_WITHOUT_PLUS_SIGN
                numobj.country_code = default_country_code
                return (default_country_code, potential_national_number)

    # No country calling code present.
    numobj.country_code = 0
    return (0, u"")


def _parse_prefix_as_idd(idd_pattern, number):
    """Strips the IDD from the start of the number if present.

    Helper function used by _maybe_strip_i18n_prefix_and_normalize().

    Returns a 2-tuple:
      - Boolean indicating if IDD was stripped
      - Number with IDD stripped
    """
    match = idd_pattern.match(number)
    if match:
        match_end = match.end()
        # Only strip this if the first digit after the match is not a 0, since
        # country calling codes cannot begin with 0.
        digit_match = _CAPTURING_DIGIT_PATTERN.search(number[match_end:])
        if digit_match:
            normalized_group = _normalize_helper(digit_match.group(1),
                                                 _DIGIT_MAPPINGS,
                                                 True)
            if normalized_group == u"0":
                return (False, number)
        return (True, number[match_end:])
    return (False, number)


def _maybe_strip_i18n_prefix_and_normalize(number, possible_idd_prefix):
    """Strips any international prefix (such as +, 00, 011) present in the
    number provided, normalizes the resulting number, and indicates if an
    international prefix was present.

    Arguments:
    number -- The non-normalized telephone number that we wish to strip any international
              dialing prefix from.
    possible_idd_prefix -- The international direct dialing prefix from the region we
              think this number may be dialed in.

    Returns a 2-tuple containing:
      - The corresponding CountryCodeSource if an international dialing prefix
        could be removed from the number, otherwise
        CountryCodeSource.FROM_DEFAULT_COUNTRY if the number did not seem to
        be in international format.
      - The number with the prefix stripped.
    """
    if len(number) == 0:
        return (CountryCodeSource.FROM_DEFAULT_COUNTRY, number)
    # Check to see if the number begins with one or more plus signs.
    m = _PLUS_CHARS_PATTERN.match(number)
    if m:
        number = number[m.end():]
        # Can now normalize the rest of the number since we've consumed the
        # "+" sign at the start.
        return (CountryCodeSource.FROM_NUMBER_WITH_PLUS_SIGN,
                _normalize(number))

    # Attempt to parse the first digits as an international prefix.
    idd_pattern = re.compile(possible_idd_prefix)
    stripped, number = _parse_prefix_as_idd(idd_pattern, number)
    if stripped:
        return (CountryCodeSource.FROM_NUMBER_WITH_IDD, _normalize(number))

    # If still not found, then try and normalize the number and then try
    # again. This shouldn't be done before, since non-numeric characters (+
    # and ~) may legally be in the international prefix.
    number = _normalize(number)
    stripped, number = _parse_prefix_as_idd(idd_pattern, number)
    if stripped:
        return (CountryCodeSource.FROM_NUMBER_WITH_IDD, number)
    else:
        return (CountryCodeSource.FROM_DEFAULT_COUNTRY, number)


def _maybe_strip_national_prefix_carrier_code(number, metadata):
    """Strips any national prefix (such as 0, 1) present in a number.

    Arguments:
    number -- The normalized telephone number that we wish to strip any
              national dialing prefix from
    metadata -- The metadata for the region that we think this number
              is from.

    Returns a 2-tuple of
     - The carrier code extracted if it is present, otherwise an empty string.
     - The number with the prefix stripped
     """
    carrier_code = u""
    possible_national_prefix = metadata.national_prefix_for_parsing
    if (len(number) == 0 or
        possible_national_prefix is None or
        len(possible_national_prefix) == 0):
        # Early return for numbers of zero length.
        return (carrier_code, number)

    # Attempt to parse the first digits as a national prefix.
    prefix_pattern = re.compile(possible_national_prefix)
    prefix_match = prefix_pattern.match(number)
    if prefix_match:
        national_number_pattern = re.compile(metadata.general_desc.national_number_pattern or "")
        # prefix_match.groups() == () implies nothing was captured by the
        # capturing groups in possible_national_prefix; therefore, no
        # transformation is necessary, and we just remove the national prefix.
        num_groups = len(prefix_match.groups())
        transform_rule = metadata.national_prefix_transform_rule
        if (transform_rule is None or
            len(transform_rule) == 0 or
            prefix_match.groups()[num_groups - 1] is None):
            # Check that the resultant number is viable. If not, return.
            national_number_match = fullmatch(national_number_pattern,
                                              number[prefix_match.end():])
            if not national_number_match:
                return (carrier_code, number)

            if (num_groups > 0 and
                prefix_match.groups(num_groups) is not None):
                carrier_code = prefix_match.group(1)
            return (carrier_code, number[prefix_match.end():])
        else:
            # Check that the resultant number is viable. If not, return. Check this by copying the
            # number and making the transformation on the copy first.
            transformed_number = re.sub(prefix_pattern, transform_rule, number, count=1)
            national_number_match = fullmatch(national_number_pattern,
                                              transformed_number)
            if not national_number_match:
                return (carrier_code, number)
            if num_groups > 1:
                carrier_code = prefix_match.group(1)
            return (carrier_code, transformed_number)
    else:
        return (carrier_code, number)


def _maybe_strip_extension(number):
    """Strip extension from the end of a number string.

    Strips any extension (as in, the part of the number dialled after the
    call is connected, usually indicated with extn, ext, x or similar) from
    the end of the number, and returns it.

    Arguments:
    number -- the non-normalized telephone number that we wish to strip the extension from.

    Returns a 2-tuple of:
     - the phone extension (or "" or not present)
     - the number before the extension.
    """
    match = _EXTN_PATTERN.search(number)
    # If we find a potential extension, and the number preceding this is a
    # viable number, we assume it is an extension.
    if match and _is_viable_phone_number(number[:match.start()]):
        # The numbers are captured into groups in the regular expression.
        for group in match.groups():
            # We go through the capturing groups until we find one that
            # captured some digits. If none did, then we will return the empty
            # string.
            if group is not None:
                return (group, number[:match.start()])
    return ("", number)


def _check_region_for_parsing(number, default_region):
    """Checks to see that the region code used is valid, or if it is not
    valid, that the number to parse starts with a + symbol so that we can
    attempt to infer the region from the number.  Returns False if it cannot
    use the region provided and the region cannot be inferred.
    """
    if not _is_valid_region_code(default_region):
        # If the number is null or empty, we can't infer the region.
        if number is None or len(number) == 0:
            return False
        match = _PLUS_CHARS_PATTERN.match(number)
        if match is None:
            return False
    return True


def parse(number, region, keep_raw_input=False,
          numobj=None, _check_region=True):
    """Parse a string and return a corresponding PhoneNumber object.

    This method with throw a NumberParseException if the number is not
    considered to be a possible number. Note that validation of whether the
    number is actually a valid number for a particular region is not
    performed. This can be done separately with is_valid_number.

    Arguments:
    number -- The number that we are attempting to parse. This can
              contain formatting such as +, ( and -, as well as a phone
              number extension.
    region -- The ISO 3166-1 two-letter region code that denotes the
              region that we are expecting the number to be from. This
              is only used if the number being parsed is not written in
              international format. The country_code for the number in
              this case would be stored as that of the default region
              supplied. If the number is guaranteed to start with a '+'
              followed by the country calling code, then None or
              UNKNOWN_REGION can be supplied.
    keep_raw_input -- Whether to populate the raw_input field of the
              PhoneNumber object with number (as well as the
              country_code_source field).
    numobj -- An optional existing PhoneNumber object to receive the
              parsing results
    _check_region -- Whether the check the supplied region parameter;
              should always be True for external callers.

    Returns a PhoneNumber object filled with the parse number.

    Raises:
    NumberParseException if the string is not considered to be a viable
    phone number or if no default region was supplied and the number is
    not in international format (does not start with +).
    """
    if numobj is None:
        numobj = PhoneNumber()
    if number is None:
        raise NumberParseException(NumberParseException.NOT_A_NUMBER,
                                   "The phone number supplied was None.")
    raw_number = number
    # Extract a possible number from the string passed in (this strips leading
    # characters that could not be the start of a phone number.)
    number = _extract_possible_number(number)
    if not _is_viable_phone_number(number):
        raise NumberParseException(NumberParseException.NOT_A_NUMBER,
                                   "The string supplied did not seem to be a phone number.")

    # Check the region supplied is valid, or that the extracted number starts
    # with some sort of + sign so the number's region can be determined.
    if _check_region and not _check_region_for_parsing(number, region):
        raise NumberParseException(NumberParseException.INVALID_COUNTRY_CODE,
                                   "Missing or invalid default region.")
    if keep_raw_input:
        numobj.raw_input = raw_number

    # Attempt to parse extension first, since it doesn't require
    # region-specific data and we want to have the non-normalised number here.
    extension, national_number = _maybe_strip_extension(number)
    if len(extension) > 0:
        numobj.extension = extension
    if region is None:
        metadata = None
    else:
        metadata = PhoneMetadata.region_metadata.get(region.upper(), None)
    country_code, normalized_national_number = _maybe_extract_country_code(national_number,
                                                                           metadata,
                                                                           keep_raw_input,
                                                                           numobj)
    if country_code != 0:
        number_region = region_code_for_country_code(country_code)
        if number_region != region:
            metadata = PhoneMetadata.region_metadata[number_region]
    else:
        # If no extracted country calling code, use the region supplied
        # instead. The national number is just the normalized version of the
        # number we were given to parse.
        national_number = _normalize(national_number)
        normalized_national_number += national_number
        if region is not None:
            country_code = metadata.country_code
            numobj.country_code = country_code
        elif keep_raw_input:
            numobj.country_code_source = None

    if len(normalized_national_number) < _MIN_LENGTH_FOR_NSN:
        raise NumberParseException(NumberParseException.TOO_SHORT_NSN,
                                   "The string supplied is too short to be a phone number.")
    if metadata is not None:
        carrier_code, normalized_national_number = _maybe_strip_national_prefix_carrier_code(normalized_national_number,
                                                                                             metadata)
        if keep_raw_input:
            numobj.preferred_domestic_carrier_code = carrier_code
    len_national_number = len(normalized_national_number)
    if len_national_number < _MIN_LENGTH_FOR_NSN:  # pragma no cover
        raise NumberParseException(NumberParseException.TOO_SHORT_NSN,
                                   "The string supplied is too short to be a phone number.")

    if len_national_number > _MAX_LENGTH_FOR_NSN:
        raise NumberParseException(NumberParseException.TOO_LONG,
                                   "The string supplied is too long to be a phone number.")
    if (normalized_national_number[0] == '0' and
        metadata is not None and
        metadata.leading_zero_possible):
        numobj.italian_leading_zero = True
    numobj.national_number = long(normalized_national_number)
    return numobj


def _is_number_match_OO(numobj1_in, numobj2_in):
    """Takes two phone number objects and compares them for equality."""
    # Make copies of the phone number so that the numbers passed in are not edited.
    numobj1 = PhoneNumber()
    numobj1.merge_from(numobj1_in)
    numobj2 = PhoneNumber()
    numobj2.merge_from(numobj2_in)
    # First clear raw_input, country_code_source and
    # preferred_domestic_carrier_code fields and any empty-string extensions
    # so that we can use the PhoneNumber equality method.
    numobj1.raw_input = None
    numobj1.country_code_source = None
    numobj1.preferred_domestic_carrier_code = None
    numobj2.raw_input = None
    numobj2.country_code_source = None
    numobj2.preferred_domestic_carrier_code = None
    if (numobj1.extension is not None and
        len(numobj1.extension) == 0):
        numobj1.extension = None
    if (numobj2.extension is not None and
        len(numobj2.extension) == 0):
        numobj2.extension = None

    # Early exit if both had extensions and these are different.
    if (numobj1.extension is not None and
        numobj2.extension is not None and
        numobj1.extension != numobj2.extension):
        return MatchType.NO_MATCH

    country_code1 = numobj1.country_code
    country_code2 = numobj2.country_code
    # Both had country_code specified.
    if country_code1 != 0 and country_code2 != 0:
        if numobj1 == numobj2:
            return MatchType.EXACT_MATCH
        elif (country_code1 == country_code2 and
              _is_national_number_suffix_of_other(numobj1, numobj2)):
            # A SHORT_NSN_MATCH occurs if there is a difference because of the
            # presence or absence of an 'Italian leading zero', the presence
            # or absence of an extension, or one NSN being a shorter variant
            # of the other.
            return MatchType.SHORT_NSN_MATCH
        # This is not a match.
        return MatchType.NO_MATCH

    # Checks cases where one or both country_code fields were not
    # specified. To make equality checks easier, we first set the country_code
    # fields to be equal.
    numobj1.country_code = country_code2
    # If all else was the same, then this is an NSN_MATCH.
    if numobj1 == numobj2:
        return MatchType.NSN_MATCH
    if _is_national_number_suffix_of_other(numobj1, numobj2):
        return MatchType.SHORT_NSN_MATCH
    return MatchType.NO_MATCH


def _is_national_number_suffix_of_other(numobj1, numobj2):
    """Returns true when one national number is the suffix of the other or both
    are the same.
    """
    nn1 = str(numobj1.national_number)
    nn2 = str(numobj2.national_number)
    # Note that endswith returns True if the numbers are equal.
    return nn1.endswith(nn2) or nn2.endswith(nn1)


def _is_number_match_SS(number1, number2):
    """Takes two phone numbers as strings and compares them for equality.

    This is a convenience wrapper for _is_number_match_OO/_is_number_match_OS.
    No default region is known.
    """
    try:
        numobj1 = parse(number1, UNKNOWN_REGION)
        return _is_number_match_OS(numobj1, number2)
    except NumberParseException, exc:
        if exc.error_type == NumberParseException.INVALID_COUNTRY_CODE:
            try:
                numobj2 = parse(number2, UNKNOWN_REGION)
                return _is_number_match_OS(numobj2, number1)
            except NumberParseException, exc2:
                if exc2.error_type == NumberParseException.INVALID_COUNTRY_CODE:
                    try:
                        numobj1 = parse(number1, None, keep_raw_input=False,
                                        _check_region=False, numobj=None)
                        numobj2 = parse(number2, None, keep_raw_input=False,
                                        _check_region=False, numobj=None)
                        return _is_number_match_OO(numobj1, numobj2)
                    except NumberParseException:
                        return MatchType.NOT_A_NUMBER

    # One or more of the phone numbers we are trying to match is not a viable
    # phone number.
    return MatchType.NOT_A_NUMBER


def _is_number_match_OS(numobj1, number2):
    """Wrapper variant of _is_number_match_OO that copes with one
    PhoneNumber object and one string."""
    # First see if the second number has an implicit country calling code, by
    # attempting to parse it.
    try:
        numobj2 = parse(number2, UNKNOWN_REGION)
        return _is_number_match_OO(numobj1, numobj2)
    except NumberParseException, exc:
        if exc.error_type == NumberParseException.INVALID_COUNTRY_CODE:
            # The second number has no country calling code. EXACT_MATCH is no
            # longer possible.  We parse it as if the region was the same as
            # that for the first number, and if EXACT_MATCH is returned, we
            # replace this with NSN_MATCH.
            region1 = region_code_for_country_code(numobj1.country_code)
            try:
                if region1 != UNKNOWN_REGION:
                    numobj2 = parse(number2, region1)
                    match = _is_number_match_OO(numobj1, numobj2)
                    if match == MatchType.EXACT_MATCH:
                        return MatchType.NSN_MATCH
                    else:
                        return match
                else:
                    # If the first number didn't have a valid country calling
                    # code, then we parse the second number without one as
                    # well.
                    numobj2 = parse(number2, None, keep_raw_input=False,
                                    _check_region=False, numobj=None)
                    return _is_number_match_OO(numobj1, numobj2)
            except NumberParseException:
                return MatchType.NOT_A_NUMBER
    # One or more of the phone numbers we are trying to match is not a viable
    # phone number.
    return MatchType.NOT_A_NUMBER


def is_number_match(num1, num2):
    """Takes two phone numbers and compares them for equality.

    For example, the numbers +1 345 657 1234 and 657 1234 are a SHORT_NSN_MATCH.
    The numbers +1 345 657 1234 and 345 657 are a NO_MATCH.

    Arguments
    num1 -- First number object or string to compare. Can contain formatting,
              and can have country calling code specified with + at the start.
    num2 -- Second number object or string to compare. Can contain formatting,
              and can have country calling code specified with + at the start.

    Returns:
     - EXACT_MATCH if the country_code, NSN, presence of a leading zero for
       Italian numbers and any extension present are the same.
     - NSN_MATCH if either or both has no region specified, and the NSNs and
       extensions are the same.
     - SHORT_NSN_MATCH if either or both has no region specified, or the
       region specified is the same, and one NSN could be a shorter version of
       the other number. This includes the case where one has an extension
       specified, and the other does not.
     - NO_MATCH otherwise.
     """
    if isinstance(num1, PhoneNumber) and isinstance(num2, PhoneNumber):
        return _is_number_match_OO(num1, num2)
    elif isinstance(num1, PhoneNumber):
        return _is_number_match_OS(num1, num2)
    elif isinstance(num2, PhoneNumber):
        return _is_number_match_OS(num2, num1)
    else:
        return _is_number_match_SS(num1, num2)


def _can_be_internationally_dialled(numobj):
    """Returns True if the number can only be dialled from within the region.

    If unknown, or the number can be dialled from outside the region
    as well, returns false. Does not check the number is a valid number.

    TODO: Make this method public when we have enough metadata to make it
    worthwhile. Currently visible for testing purposes only.

    Arguments:
    numobj -- the phone number objectfor which we want to know whether it is only diallable from
              within the region.
    """
    region_code = region_code_for_number(numobj)
    nsn = national_significant_number(numobj)
    if not _is_valid_region_code(region_code):
        return True
    metadata = PhoneMetadata.region_metadata[region_code]
    return not _is_number_matching_desc(nsn, metadata.no_international_dialling)


class NumberParseException(Exception):
    """Exception when attempting to parse a putative phone number"""
    # Invalid country code specified
    INVALID_COUNTRY_CODE = 0

    # The string passed in had fewer than 3 digits in it.
    # The number failed to match the regular expression
    # _VALID_PHONE_NUMBER in phonenumberutil.py.
    NOT_A_NUMBER = 1

    # The string started with an international dialing prefix
    # but after this was removed, it had fewer digits than any
    # valid phone number (including country code) could have.
    TOO_SHORT_AFTER_IDD = 2

    # After any country code has been stripped, the string
    # had fewer digits than any valid phone number could have.
    TOO_SHORT_NSN = 3

    # String had more digits than any valid phone number could have
    TOO_LONG = 4

    def __init__(self, error_type, msg):
        Exception.__init__(self, msg)
        self.error_type = error_type
        self._msg = msg

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"(%s) %s" % (self.error_type, self._msg)
