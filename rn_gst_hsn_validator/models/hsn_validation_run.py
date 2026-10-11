# -*- coding: utf-8 -*-
"""HSN/SAC validation run header (skeleton).

Batch / scheduled / manual runs. History immutability lands with Prompt 10.
"""

from odoo import fields, models


class RnGstHsnValidationRun(models.Model):
    _name = 'rn.gst.hsn.validation.run'
    _description = 'Armora GST HSN/SAC Validation Run'
    _order = 'id desc'

    name = fields.Char(required=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
