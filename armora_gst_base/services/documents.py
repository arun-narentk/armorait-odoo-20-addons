# -*- coding: utf-8 -*-
"""Document number and HSN/SAC normalization helpers."""

from __future__ import annotations

import re

from ..exceptions import GstFormatError, GstValidationError

# GST invoice Rule 46(b) style characters commonly accepted in Odoo l10n_in.
_DOC_ALLOWED_RE = re.compile(r'^[A-Za-z0-9\-/]+$')
_HSN_RE = re.compile(r'^\d{4}$|^\d{6}$|^\d{8}$')


def normalize_document_number(value):
    """Normalize a GST document/invoice number without changing its meaning.

    - strips leading/trailing whitespace
    - does not convert to int (leading zeros preserved)
    - does not remove significant internal characters
    - does not invent a number when empty
    """
    if value is None or value is False:
        return ''
    # Preserve as string; avoid float/int coercion of identifiers.
    return str(value).strip()


def validate_document_number(value, max_length=16, enforce_charset=False):
    """Validate a document number after normalization.

    ``enforce_charset`` applies the common GST Rule 46(b) character set when
    callers explicitly request it. Empty values are invalid.
    """
    doc = normalize_document_number(value)
    if not doc:
        raise GstValidationError('Document number is missing.')
    if max_length and len(doc) > max_length:
        raise GstFormatError(
            'Document number exceeds maximum length of %s characters.' % max_length
        )
    if enforce_charset and not _DOC_ALLOWED_RE.match(doc):
        raise GstFormatError(
            "Document number may only contain letters, digits, '-' and '/'."
        )
    return doc


def normalize_hsn_sac(value):
    """Normalize HSN/SAC by stripping whitespace. Digits only; no silent padding."""
    if value is None or value is False:
        return ''
    text = str(value).strip().replace(' ', '')
    return text


def validate_hsn_sac(value, min_digits=None):
    """Validate HSN/SAC as 4, 6, or 8 digits (optionally enforce minimum length)."""
    code = normalize_hsn_sac(value)
    if not code:
        raise GstValidationError('HSN/SAC code is missing.')
    if not code.isdigit():
        raise GstFormatError('HSN/SAC code must contain digits only.')
    if not _HSN_RE.match(code):
        raise GstFormatError('HSN/SAC code must be 4, 6, or 8 digits.')
    if min_digits is not None:
        try:
            min_digits = int(min_digits)
        except (TypeError, ValueError) as err:
            raise GstFormatError('Invalid HSN/SAC minimum digit setting.') from err
        if len(code) < min_digits:
            raise GstFormatError(
                'HSN/SAC code must be at least %s digits.' % min_digits
            )
    return code
