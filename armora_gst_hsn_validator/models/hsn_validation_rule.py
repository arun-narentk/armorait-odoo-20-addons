# -*- coding: utf-8 -*-
"""HSN/SAC validation rule registry (skeleton).

Rule codes and evaluation methods are implemented in Prompts 5–6.
"""

from odoo import fields, models


class ArmoraGstHsnValidationRule(models.Model):
    _name = 'armora.gst.hsn.validation.rule'
    _description = 'Armora GST HSN/SAC Validation Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    severity = fields.Selection(
        selection=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        default='warning',
        required=True,
    )

    _armora_gst_hsn_rule_code_uniq = models.Constraint(
        'unique(code)',
        "Validation rule code must be unique.",
    )
