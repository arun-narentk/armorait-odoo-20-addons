# -*- coding: utf-8 -*-
from odoo import fields, models


class ArmoraGstInvoiceValidationWizard(models.TransientModel):
    """Batch GST invoice validation wizard."""

    _name = 'armora.gst.invoice.validation.wizard'
    _description = 'GST Invoice Validation Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date()
    date_to = fields.Date()
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('all', 'All GST Documents'),
    ], default='all', required=True)
    partner_id = fields.Many2one('res.partner')
    invoice_ids = fields.Many2many(
        'account.move',
        string='Selected Documents',
    )
    sync_move_issues = fields.Boolean(
        string='Refresh Invoice Issues',
        default=True,
    )

    def action_validate(self):
        self.ensure_one()
        invoices = self.invoice_ids
        if not invoices and (self.date_from or self.date_to or self.partner_id or self.move_type != 'all'):
            domain = [
                ('company_id', '=', self.company_id.id),
                ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
            ]
            if self.move_type != 'all':
                domain.append(('move_type', '=', self.move_type))
            if self.partner_id:
                domain.append(('partner_id', '=', self.partner_id.id))
            if self.date_from:
                domain.append(('invoice_date', '>=', self.date_from))
            if self.date_to:
                domain.append(('invoice_date', '<=', self.date_to))
            invoices = self.env['account.move'].search(domain)

        run = self.env['armora.gst.invoice.validation'].create_for_invoices(
            invoices,
            sync_move_issues=self.sync_move_issues,
            notes='Created from batch validation wizard.',
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'GST Validation Run',
            'res_model': 'armora.gst.invoice.validation',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }
