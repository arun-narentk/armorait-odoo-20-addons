# -*- coding: utf-8 -*-
"""GSTIN normalize and structure/checksum validation (no GSTN portal calls)."""

from __future__ import annotations

import re

from ..exceptions import GstChecksumError, GstFormatError, GstValidationError

try:
    from stdnum.in_ import gstin as stdnum_gstin
except ImportError:  # pragma: no cover
    stdnum_gstin = None

# Regular / composition / casual style GSTIN (15 chars, Z in position 14).
_GSTIN_RE = re.compile(
    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
)
_CHECK_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def normalize_gstin(value):
    """Strip surrounding whitespace and uppercase. Does not invent values."""
    if value is None or value is False:
        return ''
    return str(value).strip().upper()


def get_gstin_state_code(value):
    """Return the 2-digit state TIN prefix from a normalized/raw GSTIN."""
    gstin = normalize_gstin(value)
    if len(gstin) < 2 or not gstin[:2].isdigit():
        raise GstFormatError('Cannot extract state code from GSTIN.')
    return gstin[:2]


def get_gstin_pan(value):
    """Return PAN characters (positions 3-12) from a GSTIN."""
    gstin = normalize_gstin(value)
    if len(gstin) < 12:
        raise GstFormatError('Cannot extract PAN from GSTIN.')
    return gstin[2:12]


def _checksum_valid_local(gstin):
    if len(gstin) != 15:
        return False
    factor = 1
    total = 0
    for char in gstin[:-1]:
        code = _CHECK_CHARS.find(char)
        if code < 0:
            return False
        product = factor * code
        total += (product // 36) + (product % 36)
        factor = 2 if factor == 1 else 1
    check = (36 - (total % 36)) % 36
    return _CHECK_CHARS[check] == gstin[-1]


def checksum_valid(value):
    """Return True if GSTIN checksum is valid (stdnum when available)."""
    gstin = normalize_gstin(value)
    if len(gstin) != 15:
        return False
    if stdnum_gstin is not None:
        try:
            return bool(stdnum_gstin.is_valid(gstin))
        except Exception:
            return _checksum_valid_local(gstin)
    return _checksum_valid_local(gstin)


def validate_gstin(value):
    """Validate GSTIN structure and checksum without DB or HTTP calls.

    Returns a dict:
      status: 'valid' | 'invalid'
      reason: missing | length | format | checksum | ok
      message: human-readable text
      normalized: normalized GSTIN or ''
      state_code / pan: set when format is acceptable enough to extract
    """
    raw = normalize_gstin(value)
    if not raw:
        return {
            'status': 'invalid',
            'reason': 'missing',
            'message': 'GSTIN is missing.',
            'normalized': '',
        }
    if len(raw) != 15:
        return {
            'status': 'invalid',
            'reason': 'length',
            'message': 'GSTIN must be exactly 15 characters.',
            'normalized': raw,
        }
    if not _GSTIN_RE.match(raw):
        return {
            'status': 'invalid',
            'reason': 'format',
            'message': 'GSTIN format is invalid (state + PAN + entity + Z + checksum).',
            'normalized': raw,
        }
    state_code = raw[:2]
    pan = raw[2:12]
    if not checksum_valid(raw):
        return {
            'status': 'invalid',
            'reason': 'checksum',
            'message': 'GSTIN checksum is invalid.',
            'normalized': raw,
            'state_code': state_code,
            'pan': pan,
        }
    return {
        'status': 'valid',
        'reason': 'ok',
        'message': 'GSTIN structure is valid.',
        'normalized': raw,
        'state_code': state_code,
        'pan': pan,
    }


def assert_valid_gstin(value):
    """Raise GstFormatError / GstChecksumError / GstValidationError if invalid."""
    result = validate_gstin(value)
    if result['status'] == 'valid':
        return result
    reason = result.get('reason')
    message = result.get('message') or 'Invalid GSTIN.'
    if reason == 'checksum':
        raise GstChecksumError(message)
    if reason in ('length', 'format'):
        raise GstFormatError(message)
    raise GstValidationError(message)
