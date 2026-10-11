# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ArmoraGstGstr2bLine(models.Model):
    _name = 'armora.gst.gstr2b.line'
    _description = 'GSTR-2A / GSTR-2B Reconciliation Line'
    _order = 'invoice_date, invoice_number, id'

    reconciliation_id = fields.Many2one(
        'armora.gst.gstr2b',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='reconciliation_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='reconciliation_id.currency_id', store=True)

    source = fields.Selection([
        ('gstr2b', 'GST Portal'),
        ('odoo', 'Odoo Only'),
    ], required=True, default='gstr2b', index=True)

    partner_id = fields.Many2one('res.partner', index=True, ondelete='set null')
    vendor_gstin = fields.Char(index=True)
    vendor_name = fields.Char()

    invoice_number = fields.Char(index=True)
    invoice_date = fields.Date(index=True)
    document_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
        ('debit_note', 'Debit Note'),
    ], default='invoice', required=True)

    place_of_supply = fields.Char()
    reverse_charge = fields.Boolean(default=False)
    itc_availability = fields.Selection([
        ('y', 'Yes'),
        ('n', 'No'),
        ('p', 'Provisional'),
    ], string='ITC Available')

    taxable_value = fields.Monetary(currency_field='currency_id')
    gst_rate = fields.Float(digits=(16, 2))
    cgst_amount = fields.Monetary(currency_field='currency_id')
    sgst_amount = fields.Monetary(currency_field='currency_id')
    igst_amount = fields.Monetary(currency_field='currency_id')
    cess_amount = fields.Monetary(currency_field='currency_id')
    invoice_value = fields.Monetary(currency_field='currency_id')

    # GSTR-2A only: whether the supplier filed the returns behind this invoice.
    supplier_filing_status = fields.Selection([
        ('filed', 'Filed'),
        ('not_filed', 'Not Filed'),
    ], string='Supplier GSTR-1', index=True,
        help='GSTR-1, IFF or GSTR-5 filing status of the supplier, from GSTR-2A.')
    supplier_filing_date = fields.Date(string='Supplier GSTR-1 Filed On')
    supplier_filing_period = fields.Char(string='Supplier GSTR-1 Period')
    supplier_3b_status = fields.Selection([
        ('filed', 'Filed'),
        ('not_filed', 'Not Filed'),
    ], string='Supplier GSTR-3B', index=True,
        help='GSTR-3B filing status of the supplier for the period, from GSTR-2A.')

    match_state = fields.Selection([
        ('pending', 'Pending'),
        ('matched', 'Matched'),
        ('mismatch', 'Mismatch'),
        ('missing_in_odoo', 'Missing in Odoo'),
        ('missing_in_2b', 'Missing in 2B'),
        ('ignored', 'Ignored'),
        ('disputed', 'Disputed'),
    ], default='pending', required=True, index=True)

    move_id = fields.Many2one('account.move', string='Vendor Bill', index=True, ondelete='set null')
    mismatch_detail = fields.Text()

    diff_taxable_value = fields.Monetary(currency_field='currency_id')
    diff_cgst = fields.Monetary(currency_field='currency_id')
    diff_sgst = fields.Monetary(currency_field='currency_id')
    diff_igst = fields.Monetary(currency_field='currency_id')
    diff_cess = fields.Monetary(currency_field='currency_id')

    notes = fields.Text()

    def action_open_bill(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No vendor bill is linked to this line.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_matched(self):
        for line in self:
            if not line.move_id:
                raise UserError(_('Link a vendor bill before marking as matched.'))
            line.match_state = 'matched'
            line.mismatch_detail = False
        return True

    def action_mark_ignored(self):
        self.write({'match_state': 'ignored'})
        return True

    def action_mark_disputed(self):
        self.write({'match_state': 'disputed'})
        return True

    def action_create_vendor_bill(self):
        """Create a draft vendor bill from a 2B line missing in Odoo."""
        self.ensure_one()
        if self.source != 'gstr2b':
            raise UserError(_('Vendor bills can only be created from GSTR-2B lines.'))
        if self.move_id:
            raise UserError(_('This line is already linked to a vendor bill.'))
        if self.match_state not in ('missing_in_odoo', 'pending', 'mismatch'):
            raise UserError(_('Create a bill only for lines that are missing or need review.'))

        Partner = self.env['res.partner']
        partner = self.partner_id
        if not partner and self.vendor_gstin:
            partner = Partner.search([
                ('vat', '=', self.vendor_gstin),
                '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
            ], limit=1)
        if not partner:
            partner = Partner.create({
                'name': self.vendor_name or self.vendor_gstin or _('GSTR-2B Vendor'),
                'vat': self.vendor_gstin,
                'company_type': 'company',
                'country_id': self.env.ref('base.in').id,
                'l10n_in_gst_treatment': 'regular' if self.vendor_gstin else 'unregistered',
            })
            self.partner_id = partner.id

        taxable = self.taxable_value or 0.0
        taxes = self.cgst_amount + self.sgst_amount + self.igst_amount + self.cess_amount
        # Single product-less line: accountant completes taxes/products
        move = self.env['account.move'].create({
            'move_type': 'in_invoice' if self.document_type != 'credit_note' else 'in_refund',
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'invoice_date': self.invoice_date,
            'ref': self.invoice_number,
            'narration': _(
                'Created from GSTR-2B reconciliation %s. '
                'Taxable %.2f, CGST %.2f, SGST %.2f, IGST %.2f, Cess %.2f. '
                'Complete product/tax lines before posting.'
            ) % (
                self.reconciliation_id.name,
                taxable,
                self.cgst_amount or 0.0,
                self.sgst_amount or 0.0,
                self.igst_amount or 0.0,
                self.cess_amount or 0.0,
            ),
            'invoice_line_ids': [(0, 0, {
                'name': _('GSTR-2B %s') % (self.invoice_number or _('Invoice')),
                'quantity': 1.0,
                'price_unit': taxable or (self.invoice_value or 0.0) - taxes,
            })],
        })
        self.write({
            'move_id': move.id,
            'partner_id': partner.id,
            'match_state': 'mismatch' if taxes else 'matched',
            'mismatch_detail': _(
                'Draft bill created from 2B. Review tax lines before treating as fully matched.'
            ) if taxes else False,
            'notes': (self.notes or '') + (_('\nDraft bill %s created from 2B.') % move.display_name),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def normalize_invoice_number(self, number):
        if not number:
            return ''
        return ''.join(ch for ch in str(number).upper() if ch.isalnum())
