# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class ArmoraGstFilingLine(models.Model):
    _name = 'armora.gst.filing.line'
    _description = 'GST Filing Snapshot Line'
    _order = 'invoice_date, invoice_number, id'

    filing_id = fields.Many2one(
        'armora.gst.filing',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='filing_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related='filing_id.currency_id',
        store=True,
    )

    move_id = fields.Many2one('account.move', string='Source Invoice', index=True, ondelete='set null')
    move_line_id = fields.Many2one('account.move.line', string='Source Line', index=True, ondelete='set null')

    partner_id = fields.Many2one('res.partner', index=True, ondelete='set null')
    partner_gstin = fields.Char(index=True)
    partner_name = fields.Char()

    invoice_date = fields.Date(index=True)
    invoice_number = fields.Char(index=True)

    document_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
        ('debit_note', 'Debit Note'),
    ], required=True, default='invoice', index=True)
    document_date = fields.Date()

    original_invoice_number = fields.Char()
    original_invoice_date = fields.Date()

    place_of_supply = fields.Char()
    place_of_supply_code = fields.Char(index=True)

    supply_type = fields.Selection([
        ('b2b', 'B2B'),
        ('b2cl', 'B2C Large'),
        ('b2cs', 'B2C Small'),
        ('export', 'Export'),
        ('deemed_export', 'Deemed Export'),
        ('nil_rated', 'Nil Rated'),
        ('exempt', 'Exempt'),
        ('non_gst', 'Non-GST'),
        ('cdnr', 'CDNR'),
        ('cdnur', 'CDNUR'),
    ], index=True)

    is_reverse_charge = fields.Boolean(default=False)
    is_export = fields.Boolean(default=False)

    export_type = fields.Selection([
        ('wpay', 'With Payment of Tax'),
        ('wopay', 'Without Payment of Tax'),
    ])
    port_code = fields.Char()
    shipping_bill_number = fields.Char()
    shipping_bill_date = fields.Date()

    ecommerce_gstin = fields.Char()

    hsn_code = fields.Char(index=True)
    sac_code = fields.Char()
    description = fields.Char()

    quantity = fields.Float(digits='Product Unit of Measure')
    uom = fields.Char()

    taxable_value = fields.Monetary(currency_field='currency_id')
    gst_rate = fields.Float(digits=(16, 2))

    cgst_amount = fields.Monetary(currency_field='currency_id')
    sgst_amount = fields.Monetary(currency_field='currency_id')
    igst_amount = fields.Monetary(currency_field='currency_id')
    cess_amount = fields.Monetary(currency_field='currency_id')
    total_tax = fields.Monetary(currency_field='currency_id')
    invoice_value = fields.Monetary(currency_field='currency_id')

    gst_section = fields.Char(help='Logical GSTR section key, e.g. b2b')
    gst_table = fields.Selection([
        ('b2b', 'B2B'),
        ('b2cl', 'B2CL'),
        ('b2cs', 'B2CS'),
        ('exp', 'EXP'),
        ('cdnr', 'CDNR'),
        ('cdnur', 'CDNUR'),
        ('hsn', 'HSN'),
        ('nil', 'NIL'),
        ('docs', 'DOCS'),
    ], index=True)

    validation_state = fields.Selection([
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], default='ok', index=True)
    validation_message = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            filing = self.env['armora.gst.filing'].browse(vals.get('filing_id'))
            if filing and filing.state != 'draft' and not self.env.context.get('armora_gst_regenerate_snapshot'):
                filing._raise_readonly(
                    message='GST snapshot lines are locked after data load. Use Regenerate Snapshot.'
                )
        return super().create(vals_list)

    def write(self, vals):
        # Validation annotations are not snapshot payload; they may update after load.
        validation_only = set(vals.keys()) <= {'validation_state', 'validation_message'}
        for line in self:
            if (
                line.filing_id.state != 'draft'
                and not self.env.context.get('armora_gst_regenerate_snapshot')
                and not self.env.context.get('armora_gst_validation_update')
                and not validation_only
            ):
                line.filing_id._raise_readonly(
                    message='GST snapshot lines are locked after data load. Use Regenerate Snapshot.'
                )
        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.filing_id.state != 'draft' and not self.env.context.get('armora_gst_regenerate_snapshot'):
                if line.filing_id.state in ('submitted', 'filed', 'cancelled'):
                    line.filing_id._raise_readonly()
                if not self.env.user.has_group('armora_gst_filing.group_armora_gst_filing_manager'):
                    line.filing_id._raise_readonly(
                        message='Only GST Filing Managers can remove snapshot lines after data load.'
                    )
        return super().unlink()

    def _check_business_constraints(self):
        """Return list of (severity, message) for this line. Used by validation service."""
        self.ensure_one()
        issues = []
        currency = self.currency_id
        prec = currency.decimal_places if currency else 2

        if not self.invoice_number:
            issues.append(('error', 'missing_invoice_number', 'Invoice number is missing.'))
        if not self.invoice_date:
            issues.append(('error', 'invalid_invoice_date', 'Invoice date is missing.'))
        elif self.filing_id.period_start and self.filing_id.period_end:
            if self.invoice_date < self.filing_id.period_start or self.invoice_date > self.filing_id.period_end:
                issues.append(('error', 'invalid_invoice_date', 'Invoice date is outside the filing period.'))

        if self.supply_type == 'b2b' or self.gst_table == 'b2b':
            result = self.env['armora.gst.gstin.validator'].validate(self.partner_gstin)
            if result['status'] == 'invalid':
                issues.append(('error', 'invalid_gstin' if self.partner_gstin else 'missing_gstin', result['message']))
            elif result['status'] == 'warning':
                issues.append(('warning', 'invalid_gstin', result['message']))

        if self.gst_table not in ('nil',) and not (self.hsn_code or self.sac_code):
            issues.append(('error', 'missing_hsn', 'HSN/SAC code is missing.'))

        if self.gst_table not in ('exp',) and not self.place_of_supply_code and not self.is_export:
            issues.append(('error', 'missing_place_of_supply', 'Place of supply is missing.'))

        if self.gst_rate is not None and self.gst_rate < 0:
            issues.append(('error', 'invalid_tax_rate', 'GST rate cannot be negative.'))

        if float_compare(self.taxable_value or 0.0, 0.0, precision_digits=prec) < 0 and self.document_type == 'invoice':
            issues.append(('error', 'negative_taxable', 'Taxable value cannot be negative on invoices.'))

        expected_tax = (self.cgst_amount or 0.0) + (self.sgst_amount or 0.0) + (self.igst_amount or 0.0) + (self.cess_amount or 0.0)
        if float_compare(expected_tax, self.total_tax or 0.0, precision_digits=prec) != 0:
            issues.append(('error', 'tax_mismatch', 'Total tax does not match CGST+SGST+IGST+CESS.'))

        if self.is_export or self.gst_table == 'exp':
            if not self.shipping_bill_number:
                issues.append(('error', 'missing_export_info', 'Shipping bill number is missing for export.'))
            if not self.shipping_bill_date:
                issues.append(('error', 'missing_export_info', 'Shipping bill date is missing for export.'))
            if not self.port_code:
                issues.append(('error', 'missing_export_info', 'Port code is missing for export.'))

        if self.document_type in ('credit_note', 'debit_note'):
            if not self.original_invoice_number:
                issues.append(('error', 'missing_cdn_reference', 'Original invoice number is missing for credit/debit note.'))
            if not self.original_invoice_date:
                issues.append(('error', 'missing_cdn_reference', 'Original invoice date is missing for credit/debit note.'))

        if self.move_id and self.move_id.state == 'cancel':
            issues.append(('error', 'cancelled_invoice', 'Source invoice is cancelled.'))

        return issues
