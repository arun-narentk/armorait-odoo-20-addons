# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_gstin_recheck_days = fields.Integer(
        string='GSTIN Re-check After (days)',
        default=180,
        help='A partner is due for a new portal or manual GSTIN check when its last one is older than this.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_gstin_recheck_days = fields.Integer(related='company_id.rn_gstin_recheck_days', readonly=False)
