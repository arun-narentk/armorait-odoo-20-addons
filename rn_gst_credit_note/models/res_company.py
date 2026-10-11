# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_gst_cn_block_on_error = fields.Boolean(
        string='Stop Posting Credit Notes with GST Errors',
        help='When set, a credit note with a GST error (time limit passed, more than the invoice, different '
             'tax rates...) cannot be posted. Warnings never stop posting.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_gst_cn_block_on_error = fields.Boolean(related='company_id.rn_gst_cn_block_on_error', readonly=False)
