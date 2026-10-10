# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    armora_gst_2b_date_tolerance_days = fields.Integer(
        string='GSTR-2B Date Tolerance (Days)',
        default=0,
        help='Allow invoice date difference of this many days when matching 2B to vendor bills.',
    )
    armora_gst_2b_amount_tolerance = fields.Monetary(
        string='GSTR-2B Amount Tolerance',
        currency_field='currency_id',
        default=1.0,
        help='Absolute amount difference allowed before a 2B match is treated as a mismatch.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(related='company_id.currency_id')
    armora_gst_2b_date_tolerance_days = fields.Integer(
        related='company_id.armora_gst_2b_date_tolerance_days',
        readonly=False,
    )
    armora_gst_2b_amount_tolerance = fields.Monetary(
        related='company_id.armora_gst_2b_amount_tolerance',
        readonly=False,
        currency_field='currency_id',
    )
