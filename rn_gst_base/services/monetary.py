# -*- coding: utf-8 -*-
"""Decimal-safe monetary helpers for GST tax amounts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from ..exceptions import GstMonetaryError


def _to_decimal(amount):
    if amount is None or amount is False:
        return Decimal('0')
    if isinstance(amount, Decimal):
        return amount
    try:
        # str() avoids binary float artifacts before quantize
        return Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as err:
        raise GstMonetaryError('Invalid monetary amount: %r' % (amount,)) from err


def safe_tax_amount_rounding(amount, precision_digits=2):
    """Round a tax amount with ROUND_HALF_UP. Returns ``Decimal``."""
    try:
        precision_digits = 2 if precision_digits is None else int(precision_digits)
    except (TypeError, ValueError) as err:
        raise GstMonetaryError('Invalid precision_digits.') from err
    if precision_digits < 0:
        raise GstMonetaryError('precision_digits must be >= 0.')
    quant = Decimal('1').scaleb(-precision_digits)
    return _to_decimal(amount).quantize(quant, rounding=ROUND_HALF_UP)


def round_amount(amount, precision_digits=2):
    """Compatibility helper returning ``float`` for Odoo monetary fields."""
    return float(safe_tax_amount_rounding(amount, precision_digits=precision_digits))


def compare_tax_amounts_with_tolerance(left, right, tolerance=0, precision_digits=2):
    """Return True when absolute difference is within tolerance after rounding.

    All values are handled via Decimal to avoid binary float comparison issues.
    """
    left_d = safe_tax_amount_rounding(left, precision_digits=precision_digits)
    right_d = safe_tax_amount_rounding(right, precision_digits=precision_digits)
    tol_d = safe_tax_amount_rounding(tolerance, precision_digits=precision_digits)
    if tol_d < 0:
        raise GstMonetaryError('Tolerance must be >= 0.')
    return abs(left_d - right_d) <= tol_d


def split_cgst_sgst_from_igst_amount(igst_amount, precision_digits=2):
    """Split an IGST amount into equal CGST/SGST halves (deterministic).

    Odd paise (after rounding IGST) is applied to CGST so CGST + SGST == IGST.
    """
    total = safe_tax_amount_rounding(igst_amount, precision_digits=precision_digits)
    half = safe_tax_amount_rounding(total / Decimal('2'), precision_digits=precision_digits)
    cgst = half
    sgst = total - cgst
    return cgst, sgst
