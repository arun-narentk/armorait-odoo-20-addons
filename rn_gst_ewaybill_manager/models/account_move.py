# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_ewb_missing = fields.Boolean(
        string='E-Way Bill Missing', compute='_compute_rn_ewb_missing', store=True, index='btree_not_null',
        help='Posted goods invoice (or bill from a supplier without GSTIN) at or above the company e-way bill '
             'value limit, with no e-way bill.',
    )

    @api.depends(
        'state', 'move_type', 'amount_total_signed', 'country_code', 'company_id.l10n_in_ewaybill_feature',
        'commercial_partner_id.vat',
        'company_id.rn_ewb_threshold', 'invoice_line_ids.product_id.type', 'invoice_line_ids.l10n_in_hsn_code',
        'l10n_in_ewaybill_ids.state',
    )
    def _compute_rn_ewb_missing(self):
        for move in self:
            move.rn_ewb_missing = bool(
                move.state == 'posted'
                and move.country_code == 'IN'
                and (
                    move.move_type == 'out_invoice'
                    # A registered supplier makes the e-way bill; from an unregistered one the buyer does.
                    or (move.move_type == 'in_invoice' and not move.commercial_partner_id.vat)
                )
                and move.company_id.l10n_in_ewaybill_feature
                and abs(move.amount_total_signed) >= move.company_id.rn_ewb_threshold
                and move._rn_ewb_has_goods()
                and not move.l10n_in_ewaybill_ids.filtered(lambda e: e.state != 'cancel')
            )

    def _rn_ewb_has_goods(self):
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            hsn = (line.l10n_in_hsn_code or '').strip()
            if hsn and not hsn.startswith('99'):
                return True
            if not hsn and line.product_id and line.product_id.type != 'service':
                return True
        return False
