# -*- coding: utf-8 -*-
"""Shared category / severity selections for validation runs and results."""

VALIDATION_CATEGORY_SELECTION = [
    ('GSTIN', 'GSTIN'),
    ('DOCUMENT', 'Document'),
    ('CUSTOMER', 'Customer'),
    ('VENDOR', 'Vendor'),
    ('PLACE_OF_SUPPLY', 'Place of Supply'),
    ('TAX', 'Tax'),
    ('GST_RATE', 'GST Rate'),
    ('HSN', 'HSN'),
    ('SAC', 'SAC'),
    ('INVOICE', 'Invoice'),
    ('CREDIT_NOTE', 'Credit Note'),
    ('DEBIT_NOTE', 'Debit Note'),
    ('REVERSE_CHARGE', 'Reverse Charge'),
    ('EXPORT', 'Export'),
    ('SEZ', 'SEZ'),
    ('E_INVOICE_PREREQUISITE', 'E-Invoice Prerequisite'),
    ('EWAYBILL_PREREQUISITE', 'E-Way Bill Prerequisite'),
    ('DUPLICATE', 'Duplicate'),
    ('ACCOUNTING', 'Accounting'),
]

VALIDATION_SEVERITY_SELECTION = [
    ('error', 'Error'),
    ('warning', 'Warning'),
    ('info', 'Info'),
]

VALIDATION_RESULT_STATUS_SELECTION = [
    ('open', 'Open'),
    ('resolved', 'Resolved'),
    ('ignored', 'Ignored'),
]

VALIDATION_RUN_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('running', 'Running'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]
