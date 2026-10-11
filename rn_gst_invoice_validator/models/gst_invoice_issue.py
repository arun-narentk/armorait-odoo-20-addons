# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RnGstInvoiceIssue(models.Model):
    _name = 'rn.gst.invoice.issue'
    _description = 'GST Invoice Validation Issue'
    _order = 'severity, id'

    move_id = fields.Many2one(
        'account.move',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='move_id.company_id', store=True, index=True)
    move_line_id = fields.Many2one('account.move.line', ondelete='cascade', index=True)
    partner_id = fields.Many2one(related='move_id.partner_id', store=True, index=True)

    severity = fields.Selection(
        selection=lambda self: self.env['rn.gst.selection'].severity_selection(),
        required=True,
        default='error',
        index=True,
    )
    error_type = fields.Selection(
        selection=lambda self: self.env['rn.gst.selection'].error_type_selection(),
        required=True,
        default='other',
        index=True,
    )
    message = fields.Text(required=True)
    hint = fields.Text(string='How to Fix')

    @api.model
    def _severity_rank(self, severity):
        return {'error': 0, 'warning': 1, 'review': 2, 'info': 3}.get(severity, 9)
