# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstRegistration(models.Model):
    _inherit = 'rn.gst.registration'

    rn_filing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (QRMP)'),
    ], string='Return Filing', default='monthly', required=True,
        help='Quarterly Return Monthly Payment scheme: GSTR-1 and GSTR-3B every quarter, PMT-06 in the other months.')
    rn_gstr9c_required = fields.Boolean(
        string='Files GSTR-9C',
        help='Turnover above the GSTR-9C limit (5 crore at present): a reconciliation statement is due with GSTR-9.',
    )
    rn_return_user_id = fields.Many2one(
        'res.users', string='Returns Responsible', domain="[('share', '=', False)]",
        help='Gets the reminder activities for the returns of this GSTIN.',
    )
