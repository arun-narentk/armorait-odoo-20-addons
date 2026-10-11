# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_vendor_block_posting = fields.Boolean(
        string='Stop Bills of Blocked Suppliers',
        help='A vendor bill cannot be posted when the supplier GST decision is Block.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_vendor_block_posting = fields.Boolean(related='company_id.rn_vendor_block_posting', readonly=False)
