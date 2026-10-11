# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    rn_gst_registration_id = fields.Many2one(
        'rn.gst.registration',
        string='GST Registration',
        index='btree_not_null',
        check_company=True,
        help='Invoices and bills of this journal are issued under this GSTIN. '
             'Leave empty to use the default registration of the company.',
    )

    def write(self, vals):
        res = super().write(vals)
        if vals.get('rn_gst_registration_id'):
            for journal in self:
                journal.rn_gst_registration_id._rn_fill_missing_documents(journals=journal)
        return res
