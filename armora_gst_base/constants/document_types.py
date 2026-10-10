# -*- coding: utf-8 -*-
"""GST document-type constants (shared primitives only)."""

DOC_TYPE_INVOICE = 'inv'
DOC_TYPE_CREDIT_NOTE = 'crn'
DOC_TYPE_DEBIT_NOTE = 'dbn'
DOC_TYPE_BILL_OF_SUPPLY = 'bos'
DOC_TYPE_RECEIPT_VOUCHER = 'rcv'
DOC_TYPE_PAYMENT_VOUCHER = 'pdv'
DOC_TYPE_REFUND_VOUCHER = 'rfv'
DOC_TYPE_DELIVERY_CHALLAN = 'dc'
DOC_TYPE_OTHER = 'oth'

DOCUMENT_TYPE_SELECTION = [
    (DOC_TYPE_INVOICE, 'Tax Invoice'),
    (DOC_TYPE_CREDIT_NOTE, 'Credit Note'),
    (DOC_TYPE_DEBIT_NOTE, 'Debit Note'),
    (DOC_TYPE_BILL_OF_SUPPLY, 'Bill of Supply'),
    (DOC_TYPE_RECEIPT_VOUCHER, 'Receipt Voucher'),
    (DOC_TYPE_PAYMENT_VOUCHER, 'Payment Voucher'),
    (DOC_TYPE_REFUND_VOUCHER, 'Refund Voucher'),
    (DOC_TYPE_DELIVERY_CHALLAN, 'Delivery Challan'),
    (DOC_TYPE_OTHER, 'Other'),
]
