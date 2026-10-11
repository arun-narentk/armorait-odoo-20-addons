# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .gst_vendor_profile import DECISIONS


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_vendor_decision = fields.Selection(DECISIONS, string='Supplier GST Decision',
                                          compute='_compute_rn_vendor_decision')
    rn_vendor_warning = fields.Char(compute='_compute_rn_vendor_decision')

    @api.depends('partner_id', 'company_id', 'move_type')
    def _compute_rn_vendor_decision(self):
        Profile = self.env['rn.gst.vendor.profile'].sudo()
        labels = dict(DECISIONS)
        for move in self:
            move.rn_vendor_decision = False
            move.rn_vendor_warning = False
            if move.move_type not in ('in_invoice', 'in_refund') or not move.partner_id:
                continue
            profile = Profile._rn_profile_for(move.partner_id, move.company_id)
            if not profile or profile.decision == 'allow':
                continue
            move.rn_vendor_decision = profile.decision
            move.rn_vendor_warning = _(
                'Supplier GST decision: %(decision)s (score %(score)s/100, risk %(risk)s). %(top)s',
                decision=labels[profile.decision], score=profile.score,
                risk=dict(profile._fields['risk']._description_selection(self.env))[profile.risk],
                top=profile.finding_ids[:1].message or '',
            )

    def _post(self, soft=True):
        for move in self.filtered(lambda m: m.move_type == 'in_invoice' and m.company_id.rn_vendor_block_posting):
            if move.rn_vendor_decision == 'block':
                raise UserError(_(
                    'Bills of %(partner)s cannot be posted: its supplier GST decision is Block.\n%(reason)s',
                    partner=move.partner_id.display_name, reason=move.rn_vendor_warning,
                ))
        return super()._post(soft)
