# -*- coding: utf-8 -*-
"""HSN/SAC validation finding (skeleton).

Domain fields and engine wiring are added in later prompts.
Reuse Odoo ``l10n_in_hsn_code``; do not invent a second HSN Char on products.
"""

from odoo import fields, models


class ArmoraGstHsnValidationResult(models.Model):
    _name = 'armora.gst.hsn.validation.result'
    _description = 'Armora GST HSN/SAC Validation Result'
    _order = 'id desc'

    name = fields.Char(required=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    # Placeholders for Prompt 4+ (source, code, status, severity, rule, …)
