# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rn_gst_reminder_days = fields.Integer(
        string='GST Return Reminder (days before)',
        default=5,
        help='The person responsible for a GST return gets a to-do this many days before its due date.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rn_gst_reminder_days = fields.Integer(related='company_id.rn_gst_reminder_days', readonly=False)
