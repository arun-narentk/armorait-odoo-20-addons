# -*- coding: utf-8 -*-
# Shared GST constants for the Armora GST foundation layer.
# Registration model itself is implemented in a later step.

from .document_types import DOCUMENT_TYPE_SELECTION
from .filing import FILING_STATUS_SELECTION, FILING_TYPE_SELECTION
from .rates import STANDARD_GST_RATES, TAX_TYPE_SELECTION
from .registration import REGISTRATION_TYPE_SELECTION
from .severity import SEVERITY_SELECTION
from .state_codes import OFFICIAL_GST_TIN_CODES, TIN_FOREIGN_COUNTRY, TIN_OTHER_TERRITORY
from .transaction import SUPPLY_NATURE_SELECTION, TRANSACTION_TYPE_SELECTION

__all__ = [
    'DOCUMENT_TYPE_SELECTION',
    'FILING_STATUS_SELECTION',
    'FILING_TYPE_SELECTION',
    'STANDARD_GST_RATES',
    'TAX_TYPE_SELECTION',
    'REGISTRATION_TYPE_SELECTION',
    'SEVERITY_SELECTION',
    'OFFICIAL_GST_TIN_CODES',
    'TIN_FOREIGN_COUNTRY',
    'TIN_OTHER_TERRITORY',
    'SUPPLY_NATURE_SELECTION',
    'TRANSACTION_TYPE_SELECTION',
]
