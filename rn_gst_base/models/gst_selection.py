# -*- coding: utf-8 -*-
from odoo import api, models

from ..constants.document_types import DOCUMENT_TYPE_SELECTION
from ..constants.filing import FILING_STATUS_SELECTION, FILING_TYPE_SELECTION
from ..constants.registration import REGISTRATION_TYPE_SELECTION
from ..constants.severity import SEVERITY_SELECTION
from ..constants.transaction import SUPPLY_NATURE_SELECTION, TRANSACTION_TYPE_SELECTION


class RnGstSelection(models.AbstractModel):
    """Shared selection definitions for the Armora GST Suite."""

    _name = 'rn.gst.selection'
    _description = 'Armora GST Shared Selections'

    @api.model
    def severity_selection(self):
        return list(SEVERITY_SELECTION)

    @api.model
    def filing_type_selection(self):
        return list(FILING_TYPE_SELECTION)

    @api.model
    def filing_status_selection(self):
        return list(FILING_STATUS_SELECTION)

    @api.model
    def document_type_selection(self):
        return list(DOCUMENT_TYPE_SELECTION)

    @api.model
    def transaction_type_selection(self):
        return list(TRANSACTION_TYPE_SELECTION)

    @api.model
    def supply_nature_selection(self):
        return list(SUPPLY_NATURE_SELECTION)

    @api.model
    def registration_type_selection(self):
        return list(REGISTRATION_TYPE_SELECTION)

    @api.model
    def error_type_selection(self):
        # Kept for downstream modules (validator / filing). Domain-specific
        # error catalogs may move to those modules later; do not expand here.
        return [
            ('missing_gstin', 'Missing GSTIN'),
            ('invalid_gstin', 'Invalid GSTIN'),
            ('missing_hsn', 'Missing HSN'),
            ('missing_sac', 'Missing SAC'),
            ('missing_place_of_supply', 'Missing Place of Supply'),
            ('pos_gstin_mismatch', 'Place of Supply / GSTIN Mismatch'),
            ('invalid_tax_rate', 'Invalid Tax Rate'),
            ('tax_mismatch', 'Tax Calculation Mismatch'),
            ('tax_type_mismatch', 'CGST/SGST/IGST Type Mismatch'),
            ('duplicate_invoice', 'Duplicate Invoice'),
            ('missing_invoice_number', 'Missing Invoice Number'),
            ('invalid_invoice_date', 'Invalid Invoice Date'),
            ('invoice_series', 'Invoice Series / Numbering'),
            ('missing_export_info', 'Missing Export Information'),
            ('missing_cdn_reference', 'Missing Credit/Debit Note Reference'),
            ('cancelled_invoice', 'Cancelled Invoice'),
            ('missing_tax_configuration', 'Missing Tax Configuration'),
            ('rcm_mismatch', 'Reverse Charge Mismatch'),
            ('reconciliation', 'Reconciliation Difference'),
            ('missing_in_odoo', 'Missing in Odoo'),
            ('missing_in_2b', 'Missing in GSTR-2B'),
            ('einvoice_pending', 'E-Invoice Pending'),
            ('einvoice_failed', 'E-Invoice Failed'),
            ('einvoice_eligibility', 'E-Invoice Eligibility'),
            ('ewaybill_pending', 'E-Way Bill Pending'),
            ('negative_taxable', 'Negative Taxable Value'),
            ('other', 'Other'),
        ]
