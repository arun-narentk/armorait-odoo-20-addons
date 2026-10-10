# -*- coding: utf-8 -*-
"""GST filing status and return-type constants.

These are shared labels only. Filing workflows live in dedicated modules.
"""

FILING_TYPE_GSTR1 = 'gstr1'
FILING_TYPE_GSTR1A = 'gstr1a'
FILING_TYPE_GSTR3B = 'gstr3b'
FILING_TYPE_GSTR9 = 'gstr9'
FILING_TYPE_GSTR2B = 'gstr2b'

FILING_TYPE_SELECTION = [
    (FILING_TYPE_GSTR1, 'GSTR-1'),
    (FILING_TYPE_GSTR1A, 'GSTR-1A'),
    (FILING_TYPE_GSTR3B, 'GSTR-3B'),
    (FILING_TYPE_GSTR9, 'GSTR-9'),
    (FILING_TYPE_GSTR2B, 'GSTR-2B'),
]

FILING_STATUS_DRAFT = 'draft'
FILING_STATUS_DATA_LOADED = 'data_loaded'
# Alias kept for older references; prefer FILING_STATUS_DATA_LOADED.
FILING_STATUS_LOADED = FILING_STATUS_DATA_LOADED
FILING_STATUS_VALIDATED = 'validated'
FILING_STATUS_READY = 'ready'
FILING_STATUS_GENERATED = 'generated'
FILING_STATUS_SUBMITTED = 'submitted'
FILING_STATUS_FILED = 'filed'
FILING_STATUS_CANCELLED = 'cancelled'

FILING_STATUS_SELECTION = [
    (FILING_STATUS_DRAFT, 'Draft'),
    (FILING_STATUS_DATA_LOADED, 'Data Loaded'),
    (FILING_STATUS_VALIDATED, 'Validated'),
    (FILING_STATUS_READY, 'Ready'),
    (FILING_STATUS_GENERATED, 'File Generated'),
    (FILING_STATUS_SUBMITTED, 'Submitted'),
    (FILING_STATUS_FILED, 'Filed'),
    (FILING_STATUS_CANCELLED, 'Cancelled'),
]
