# -*- coding: utf-8 -*-
"""GST rate utility helpers (primitives only, no filing classification)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from ..constants.rates import STANDARD_GST_RATES
from ..exceptions import GstValidationError


def _to_rate(value):
    if value is None or value is False:
        raise GstValidationError('GST rate is missing.')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as err:
        raise GstValidationError('Invalid GST rate: %r' % (value,)) from err


def normalize_gst_rate(value):
    """Normalize a GST rate to ``Decimal`` (no silent correction of unknowns)."""
    return _to_rate(value)


def is_standard_gst_rate(value):
    """Return True if rate is in the known common GST rate set."""
    try:
        return _to_rate(value) in STANDARD_GST_RATES
    except GstValidationError:
        return False


def split_igst_rate_to_cgst_sgst(igst_rate):
    """Split an IGST rate into equal CGST/SGST rates.

    Raises if the IGST rate is not evenly divisible into two equal halves
    at decimal precision (does not invent unsupported rate splits).
    """
    rate = _to_rate(igst_rate)
    half = rate / Decimal('2')
    if half * Decimal('2') != rate:
        raise GstValidationError(
            'IGST rate %s cannot be split evenly into CGST/SGST.' % rate
        )
    return half, half
