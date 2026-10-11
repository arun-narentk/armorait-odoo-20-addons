# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    rn_itc_treatment = fields.Selection([
        ('eligible', 'Eligible'),
        ('blocked', 'Blocked (section 17(5))'),
        ('common', 'Common credit (Rule 42)'),
    ], string='ITC Type', default='eligible', copy=True,
        help='How the GST credit on this bill line is treated in the ITC ledger: '
             'blocked credit is reversed in full, common credit is reversed in the ratio '
             'of exempt to total turnover of the month.')
