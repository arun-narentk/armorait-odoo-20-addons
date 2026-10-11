# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_einv_30_day_rule = fields.Boolean(
        string='E-Invoice 30-Day Limit',
        help='Turnover of 10 crore or more: an invoice must be reported to the IRP within 30 days of its date.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_einv_30_day_rule = fields.Boolean(related='company_id.rn_einv_30_day_rule', readonly=False)
