# -*- coding: utf-8 -*-
"""GST rate change request (skeleton).

Draft changes must not alter live account.tax until explicit apply (Prompt 9–10).
"""

from odoo import fields, models


class ArmoraGstRateChange(models.Model):
    _name = 'armora.gst.rate.change'
    _description = 'Armora GST Rate Change'
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
            ('review', 'Review'),
            ('approved', 'Approved'),
            ('scheduled', 'Scheduled'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    rate_id = fields.Many2one('armora.gst.rate', string='Rate Definition', index=True)
    note = fields.Text()
