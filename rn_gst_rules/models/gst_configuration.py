# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_gst_api_environment = fields.Selection(
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        string='Armora GST API Environment',
        default='sandbox',
    )
    rn_gst_api_provider = fields.Char(
        string='GST API Provider',
        default='odoo_iap_tera',
        help='Logical provider key. Endpoints are resolved from environment, not hard-coded.',
    )
    rn_gst_api_version = fields.Char(
        string='GST API Version',
        default='1',
    )
    rn_gst_enable_einvoice = fields.Boolean(string='Enable Armora E-Invoice Extensions', default=True)
    rn_gst_enable_ewaybill = fields.Boolean(string='Enable Armora E-Way Bill Extensions', default=True)
    rn_gst_enable_ewaybill_closure = fields.Boolean(
        string='Enable Voluntary E-Way Bill Closure',
        default=True,
    )
    rn_gst_validation_mode = fields.Selection(
        selection=[
            ('advisory', 'Advisory (warnings only)'),
            ('blocking', 'Blocking (errors stop API submit)'),
            ('strict', 'Strict (errors and configured warnings block)'),
        ],
        string='GST Validation Mode',
        default='blocking',
    )
    rn_gst_ewaybill_close_path = fields.Char(
        string='EWB Closure API Path',
        default='/iap/l10n_in_edi_ewaybill/1/close',
        help='IAP / GSP relative path for voluntary EWB closure. Confirm against current sandbox specs.',
    )
    rn_gst_post_closure_actions_allowed = fields.Boolean(
        string='Allow Post-Closure EWB Actions',
        default=True,
        help='During GSTN stabilisation, transporter/vehicle/extend may remain allowed after closure.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_gst_api_environment = fields.Selection(
        related='company_id.rn_gst_api_environment',
        readonly=False,
    )
    rn_gst_api_provider = fields.Char(
        related='company_id.rn_gst_api_provider',
        readonly=False,
    )
    rn_gst_api_version = fields.Char(
        related='company_id.rn_gst_api_version',
        readonly=False,
    )
    rn_gst_enable_einvoice = fields.Boolean(
        related='company_id.rn_gst_enable_einvoice',
        readonly=False,
    )
    rn_gst_enable_ewaybill = fields.Boolean(
        related='company_id.rn_gst_enable_ewaybill',
        readonly=False,
    )
    rn_gst_enable_ewaybill_closure = fields.Boolean(
        related='company_id.rn_gst_enable_ewaybill_closure',
        readonly=False,
    )
    rn_gst_validation_mode = fields.Selection(
        related='company_id.rn_gst_validation_mode',
        readonly=False,
    )
    rn_gst_ewaybill_close_path = fields.Char(
        related='company_id.rn_gst_ewaybill_close_path',
        readonly=False,
        groups='rn_gst_base.group_rn_gst_administrator',
    )
    rn_gst_post_closure_actions_allowed = fields.Boolean(
        related='company_id.rn_gst_post_closure_actions_allowed',
        readonly=False,
    )
