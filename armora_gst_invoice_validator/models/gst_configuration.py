# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    armora_gst_block_post_on_error = fields.Boolean(
        string='Block Posting on GST Errors',
        default=True,
        help='When enabled, Indian GST invoices/bills with critical Armora GST validation '
             'errors cannot be posted until fixed (or overridden by a manager).',
    )
    armora_gst_validate_purchases = fields.Boolean(
        string='Validate Vendor Bills',
        default=True,
    )
    armora_gst_validate_sales = fields.Boolean(
        string='Validate Customer Invoices',
        default=True,
    )
    armora_gst_strict_pos_gstin = fields.Boolean(
        string='Strict Place of Supply vs GSTIN State',
        default=True,
        help='When enabled, a registered partner GSTIN state that differs from place of supply '
             'is a blocking error. Disable if you regularly bill one GSTIN and deliver to another state.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    armora_gst_block_post_on_error = fields.Boolean(
        related='company_id.armora_gst_block_post_on_error',
        readonly=False,
    )
    armora_gst_validate_purchases = fields.Boolean(
        related='company_id.armora_gst_validate_purchases',
        readonly=False,
    )
    armora_gst_validate_sales = fields.Boolean(
        related='company_id.armora_gst_validate_sales',
        readonly=False,
    )
    armora_gst_strict_pos_gstin = fields.Boolean(
        related='company_id.armora_gst_strict_pos_gstin',
        readonly=False,
    )
