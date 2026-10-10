# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    armora_gst_b2cl_threshold = fields.Monetary(
        string='B2CL Threshold',
        currency_field='currency_id',
        default=250000.0,
        help='Interstate B2C invoices above this invoice value are classified as B2CL.',
    )
    armora_gst_recon_tolerance = fields.Monetary(
        string='GST Reconciliation Tolerance',
        currency_field='currency_id',
        default=1.0,
        help='Absolute amount difference allowed before reconciliation becomes a blocking error.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(related='company_id.currency_id')
    armora_gst_b2cl_threshold = fields.Monetary(
        related='company_id.armora_gst_b2cl_threshold',
        readonly=False,
        currency_field='currency_id',
    )
    armora_gst_recon_tolerance = fields.Monetary(
        related='company_id.armora_gst_recon_tolerance',
        readonly=False,
        currency_field='currency_id',
    )
