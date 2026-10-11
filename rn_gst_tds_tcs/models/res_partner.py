# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rn_gst_tds_deductor = fields.Boolean(
        string='GST TDS Deductor',
        help='Customer that deducts GST TDS under section 51, e.g. a government department or PSU.',
    )
    rn_gst_tcs_operator = fields.Boolean(
        string='E-commerce Operator (GST TCS)',
        help='Marketplace that collects GST TCS under section 52 on sales made through it.',
    )
