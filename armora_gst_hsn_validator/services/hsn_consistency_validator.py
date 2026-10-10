# -*- coding: utf-8 -*-
"""Level 2: master-data / transaction consistency checks.

Compares codes against product, invoice line and company digit policy.
Does not invent Odoo fields; uses ``l10n_in_hsn_code`` only.
"""


def validate_consistency(context):
    """Return structured consistency findings. Implemented in Prompt 5–6."""
    return {
        'consistent': None,
        'context': context or {},
        'errors': ['not_implemented'],
        'warnings': [],
    }
