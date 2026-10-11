# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_ewb_threshold = fields.Monetary(
        string='E-Way Bill Value Limit', currency_field='currency_id', default=50000.0,
        help='Goods invoices of this value or more need an e-way bill. Some states use a higher limit '
             'for movement inside the state.',
    )
    rn_ewb_warn_days = fields.Integer(
        string='E-Way Bill Expiry Warning (days)', default=1,
        help='An active e-way bill is "expiring soon" when it is valid for this many days or less.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_ewb_threshold = fields.Monetary(related='company_id.rn_ewb_threshold', readonly=False,
                                       currency_field='currency_id')
    rn_ewb_warn_days = fields.Integer(related='company_id.rn_ewb_warn_days', readonly=False)
