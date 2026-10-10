# -*- coding: utf-8 -*-
"""Bulk HSN/SAC validation wizard (skeleton).

Selection scopes and execution land in Prompt 9.
"""

from odoo import fields, models


class ArmoraGstHsnValidationWizard(models.TransientModel):
    _name = 'armora.gst.hsn.validation.wizard'
    _description = 'Armora GST HSN/SAC Bulk Validation Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    note = fields.Text(
        readonly=True,
        default='Bulk validation will be available after the validation engine is implemented.',
    )

    def action_validate(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
