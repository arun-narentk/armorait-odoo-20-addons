# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    armora_gst_tds_threshold = fields.Monetary(
        string='GST TDS Threshold', currency_field='currency_id', default=250000.0,
        help='GST TDS applies to invoices whose taxable value is above this amount (section 51 contract value).',
    )
    armora_gst_tds_rate = fields.Float(string='GST TDS Rate %', digits=(16, 2), default=2.0)
    armora_gst_tcs_rate = fields.Float(
        string='GST TCS Rate %', digits=(16, 2), default=0.5,
        help='Rate on the net value of taxable supplies made through an e-commerce operator.',
    )
    armora_gst_tds_tcs_account_id = fields.Many2one(
        'account.account', string='TDS/TCS Credit Account',
        help='Account debited when a TDS/TCS credit is accepted, e.g. "GST TDS/TCS Receivable".',
    )
    armora_gst_tds_tcs_journal_id = fields.Many2one(
        'account.journal', string='TDS/TCS Journal', domain="[('type', '=', 'general')]",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    armora_gst_tds_threshold = fields.Monetary(related='company_id.armora_gst_tds_threshold', readonly=False,
                                               currency_field='currency_id')
    armora_gst_tds_rate = fields.Float(related='company_id.armora_gst_tds_rate', readonly=False)
    armora_gst_tcs_rate = fields.Float(related='company_id.armora_gst_tcs_rate', readonly=False)
    armora_gst_tds_tcs_account_id = fields.Many2one(related='company_id.armora_gst_tds_tcs_account_id', readonly=False)
    armora_gst_tds_tcs_journal_id = fields.Many2one(related='company_id.armora_gst_tds_tcs_journal_id', readonly=False)
