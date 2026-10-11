# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    rn_cn_reason_id = fields.Many2one('rn.gst.credit.note.reason', string='GST Reason')

    def _prepare_default_reversal(self, move):
        vals = super()._prepare_default_reversal(move)
        if self.rn_cn_reason_id and move.is_invoice():
            vals['rn_cn_reason_id'] = self.rn_cn_reason_id.id
        return vals
