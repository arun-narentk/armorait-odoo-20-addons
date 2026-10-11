# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_customer_warning = fields.Char(compute='_compute_rn_customer_warning')

    @api.depends('partner_id', 'company_id', 'move_type')
    def _compute_rn_customer_warning(self):
        Profile = self.env['rn.gst.customer.profile'].sudo()
        for move in self:
            move.rn_customer_warning = False
            if move.move_type not in ('out_invoice', 'out_refund') or not move.partner_id:
                continue
            profile = Profile._rn_profile_for(move.partner_id, move.company_id)
            if profile.risk == 'high':
                move.rn_customer_warning = _(
                    'Customer GST risk is high (score %(score)s/100). %(top)s',
                    score=profile.score, top=profile.finding_ids[:1].message or '',
                )
