# -*- coding: utf-8 -*-
"""Read-only mapping checks between Armora rates and account.tax.

Do not modify Odoo taxes from normal validation paths.
"""


def validate_tax_mapping(env, rate=None):
    """Return mapping validation result. Implemented in Prompt 8."""
    del env
    return {
        'status': 'pending',
        'valid': None,
        'issues': [],
        'message': 'GST tax mapping validation is not implemented yet.',
        'rate': rate,
    }


def get_odoo_tax_mapping(env, rate=None):
    """Return linked Odoo taxes for a rate definition. Implemented in Prompt 8."""
    del env
    return {
        'cgst_tax': False,
        'sgst_tax': False,
        'igst_tax': False,
        'cess_tax': False,
        'group_tax': False,
        'rate': rate,
    }
