# -*- coding: utf-8 -*-
"""GST transaction classification constants (labels only, no filing rules)."""

TXN_B2B = 'b2b'
TXN_B2CL = 'b2cl'
TXN_B2CS = 'b2cs'
TXN_EXPORT = 'export'
TXN_SEZ = 'sez'
TXN_DEEMED_EXPORT = 'deemed_export'
TXN_CDN = 'cdn'
TXN_CDNR = 'cdnr'
TXN_CDNUR = 'cdnur'
TXN_NIL = 'nil'
TXN_EXEMPT = 'exempt'
TXN_NON_GST = 'non_gst'
TXN_ADVANCE = 'advance'
TXN_OTHER = 'other'

TRANSACTION_TYPE_SELECTION = [
    (TXN_B2B, 'B2B'),
    (TXN_B2CL, 'B2CL'),
    (TXN_B2CS, 'B2CS'),
    (TXN_EXPORT, 'Export'),
    (TXN_SEZ, 'SEZ'),
    (TXN_DEEMED_EXPORT, 'Deemed Export'),
    (TXN_CDN, 'Credit/Debit Note'),
    (TXN_CDNR, 'CDNR'),
    (TXN_CDNUR, 'CDNUR'),
    (TXN_NIL, 'Nil Rated'),
    (TXN_EXEMPT, 'Exempt'),
    (TXN_NON_GST, 'Non-GST'),
    (TXN_ADVANCE, 'Advance'),
    (TXN_OTHER, 'Other'),
]

SUPPLY_INTRA = 'intra'
SUPPLY_INTER = 'inter'
SUPPLY_EXPORT = 'export'
SUPPLY_IMPORT = 'import'
SUPPLY_OTHER = 'other'

SUPPLY_NATURE_SELECTION = [
    (SUPPLY_INTRA, 'Intra-State'),
    (SUPPLY_INTER, 'Inter-State'),
    (SUPPLY_EXPORT, 'Export'),
    (SUPPLY_IMPORT, 'Import'),
    (SUPPLY_OTHER, 'Other'),
]
