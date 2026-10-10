# -*- coding: utf-8 -*-
"""Bulk GST rate update wizard (skeleton).

Preview / confirm / apply lands in Prompt 10. Never silently modify taxes.
"""

from odoo import fields, models


class ArmoraGstRateBulkUpdateWizard(models.TransientModel):
    _name = 'armora.gst.rate.bulk.update.wizard'
    _description = 'Armora GST Rate Bulk Update Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    note = fields.Text(
        readonly=True,
        default=(
            'Bulk rate updates will require validation, preview and explicit confirmation. '
            'Draft changes never alter live Odoo taxes until apply is implemented.'
        ),
    )

    def action_close(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
