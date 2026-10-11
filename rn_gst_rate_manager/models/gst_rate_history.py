# -*- coding: utf-8 -*-
"""Immutable GST rate change history (skeleton).

Append-only audit records are enforced in Prompt 16.
"""

from odoo import fields, models


class RnGstRateHistory(models.Model):
    _name = 'rn.gst.rate.history'
    _description = 'Armora GST Rate History'
    _order = 'id desc'

    name = fields.Char(required=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    rate_id = fields.Many2one('rn.gst.rate', index=True)
    change_id = fields.Many2one('rn.gst.rate.change', index=True)
    note = fields.Text()
