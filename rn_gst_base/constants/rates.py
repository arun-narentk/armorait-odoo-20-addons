# -*- coding: utf-8 -*-
"""Common GST rate constants and helpers (primitives only)."""

from decimal import Decimal

# Commonly notified GST rates. Not an exhaustive legal schedule.
STANDARD_GST_RATES = frozenset({
    Decimal('0'),
    Decimal('0.25'),
    Decimal('3'),
    Decimal('5'),
    Decimal('12'),
    Decimal('18'),
    Decimal('28'),
})

TAX_TYPE_IGST = 'igst'
TAX_TYPE_CGST = 'cgst'
TAX_TYPE_SGST = 'sgst'
TAX_TYPE_CESS = 'cess'

TAX_TYPE_SELECTION = [
    (TAX_TYPE_IGST, 'IGST'),
    (TAX_TYPE_CGST, 'CGST'),
    (TAX_TYPE_SGST, 'SGST'),
    (TAX_TYPE_CESS, 'CESS'),
]
