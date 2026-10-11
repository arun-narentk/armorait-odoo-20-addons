# -*- coding: utf-8 -*-
"""Level 1: HSN/SAC format validation (no external API).

Will wrap ``rn_gst_base.services.documents.validate_hsn_sac``.
Must never claim government approval from a successful format check.
"""


def validate_format(code, min_digits=None):
    """Return a structured format result. Implemented in Prompt 5."""
    return {
        'format_valid': None,
        'code': code,
        'min_digits': min_digits,
        'errors': ['not_implemented'],
        'warnings': [],
    }
