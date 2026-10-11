# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RnGstComplianceReviewWizard(models.TransientModel):
    _name = 'rn.gst.compliance.review.wizard'
    _description = 'Approve GST Readiness'

    move_ids = fields.Many2many('account.move', string='Invoices')
    blocked_count = fields.Integer(compute='_compute_counts')
    review_count = fields.Integer(compute='_compute_counts')
    note = fields.Text(help='Needed when blocked invoices are approved.')

    @api.depends('move_ids')
    def _compute_counts(self):
        for wizard in self:
            wizard.blocked_count = len(wizard.move_ids.filtered(lambda m: m.rn_gst_readiness == 'blocked'))
            wizard.review_count = len(wizard.move_ids.filtered(lambda m: m.rn_gst_readiness in ('review', 'not_checked')))

    def action_approve(self):
        self.ensure_one()
        self.move_ids._rn_gst_approve(self.note)
        return {'type': 'ir.actions.act_window_close'}
