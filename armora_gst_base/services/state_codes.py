# -*- coding: utf-8 -*-
"""Indian GST state TIN code utilities (codes, not hard-coded state names)."""

from __future__ import annotations

from ..constants.state_codes import (
    OFFICIAL_GST_TIN_CODES,
    TIN_FOREIGN_COUNTRY,
    TIN_OTHER_TERRITORY,
)
from ..exceptions import GstFormatError, GstValidationError


def normalize_state_code(value):
    """Normalize a GST state TIN to a 2-digit string.

    Accepts int/str like 29, '29', '9', '09'. Does not map names to codes.
    """
    if value is None or value is False:
        return ''
    text = str(value).strip()
    if not text:
        return ''
    if not text.isdigit():
        raise GstFormatError('GST state code must be numeric.')
    code = text.zfill(2)
    if len(code) != 2:
        raise GstFormatError('GST state code must be exactly 2 digits.')
    return code


def is_known_gst_tin(value):
    """Return True if the code is in the known official TIN set."""
    try:
        code = normalize_state_code(value)
    except GstFormatError:
        return False
    return code in OFFICIAL_GST_TIN_CODES


def validate_state_code(value, require_known=True):
    """Validate and return a normalized 2-digit TIN code."""
    code = normalize_state_code(value)
    if not code:
        raise GstValidationError('GST state code is missing.')
    if require_known and code not in OFFICIAL_GST_TIN_CODES:
        raise GstValidationError('GST state code %s is not a known TIN.' % code)
    return code


def is_special_territory_code(value):
    """Return True for foreign (96) / other territory (97) TIN codes."""
    try:
        code = normalize_state_code(value)
    except GstFormatError:
        return False
    return code in (TIN_FOREIGN_COUNTRY, TIN_OTHER_TERRITORY)


def state_codes_match(left, right):
    """Compare two TIN codes after normalization."""
    return normalize_state_code(left) == normalize_state_code(right)
