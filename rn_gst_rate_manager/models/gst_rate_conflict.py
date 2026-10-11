# -*- coding: utf-8 -*-
"""GST rate conflict / validation finding (skeleton).

Structured conflict engine lands in Prompt 12.
"""

from odoo import fields, models


class RnGstRateConflict(models.Model):
    _name = 'rn.gst.rate.conflict'
    _description = 'Armora GST Rate Conflict'
    _order = 'id desc'

    name = fields.Char(required=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    severity = fields.Selection(
        selection=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        default='warning',
        required=True,
        index=True,
    )
    rate_id = fields.Many2one('rn.gst.rate', index=True)
    active = fields.Boolean(default=True)
    note = fields.Text()
