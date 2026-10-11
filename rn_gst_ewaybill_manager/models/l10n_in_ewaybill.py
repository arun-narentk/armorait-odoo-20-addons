# -*- coding: utf-8 -*-
import math
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.fields import Domain

KM_PER_DAY = 200


class L10nInEwaybill(models.Model):
    _inherit = 'l10n.in.ewaybill'

    rn_ewb_stage = fields.Selection([
        ('to_generate', 'To Generate'),
        ('failed', 'Failed'),
        ('generated', 'Generated'),
        ('cancelled', 'Cancelled'),
    ], string='Stage', compute='_compute_rn_ewb_stage', store=True, index=True)
    rn_ewb_days_left = fields.Integer(string='Days Left', compute='_compute_rn_ewb_validity')
    rn_ewb_expiring = fields.Boolean(string='Expiring Soon', compute='_compute_rn_ewb_validity',
                                     search='_search_rn_ewb_expiring')
    rn_ewb_expired = fields.Boolean(string='Expired', compute='_compute_rn_ewb_validity',
                                    search='_search_rn_ewb_expired')
    rn_ewb_expected_days = fields.Integer(
        string='Validity by Distance (days)', compute='_compute_rn_ewb_expected_days',
        help='1 day for every 200 km or part of it, for normal cargo.',
    )
    rn_ewb_partner_id = fields.Many2one('res.partner', string='Party', compute='_compute_rn_ewb_partner',
                                        store=True, index='btree_not_null')
    rn_ewb_amount = fields.Monetary(string='Document Value', compute='_compute_rn_ewb_partner', store=True,
                                    currency_field='company_currency_id')

    @api.depends('state', 'error_message')
    def _compute_rn_ewb_stage(self):
        for ewb in self:
            if ewb.state == 'generated':
                ewb.rn_ewb_stage = 'generated'
            elif ewb.state == 'cancel':
                ewb.rn_ewb_stage = 'cancelled'
            else:
                ewb.rn_ewb_stage = 'failed' if ewb.error_message else 'to_generate'

    @api.depends('ewaybill_expiry_date', 'rn_ewb_stage')
    def _compute_rn_ewb_validity(self):
        today = fields.Date.context_today(self)
        for ewb in self:
            expiry = ewb.ewaybill_expiry_date
            live = ewb.rn_ewb_stage == 'generated' and expiry
            days = (expiry - today).days if live else 0
            ewb.rn_ewb_days_left = max(days, 0)
            ewb.rn_ewb_expired = bool(live and days < 0)
            ewb.rn_ewb_expiring = bool(live and 0 <= days <= ewb.company_id.rn_ewb_warn_days)

    def _search_rn_ewb_expiring(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        today = fields.Date.context_today(self)
        days = self.env.company.rn_ewb_warn_days
        domain = Domain('rn_ewb_stage', '=', 'generated') & Domain('ewaybill_expiry_date', '>=', today) & Domain(
            'ewaybill_expiry_date', '<=', today + timedelta(days=days))
        return domain if (operator == '=') == value else ~domain

    def _search_rn_ewb_expired(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('rn_ewb_stage', '=', 'generated') & Domain(
            'ewaybill_expiry_date', '<', fields.Date.context_today(self))
        return domain if (operator == '=') == value else ~domain

    @api.depends('distance')
    def _compute_rn_ewb_expected_days(self):
        for ewb in self:
            ewb.rn_ewb_expected_days = max(math.ceil((ewb.distance or 0) / KM_PER_DAY), 1) if ewb.distance else 0

    @api.depends('account_move_id.commercial_partner_id', 'account_move_id.amount_total_signed', 'partner_bill_to_id')
    def _compute_rn_ewb_partner(self):
        for ewb in self:
            move = ewb.account_move_id
            ewb.rn_ewb_partner_id = move.commercial_partner_id or ewb.partner_bill_to_id.commercial_partner_id
            ewb.rn_ewb_amount = abs(move.amount_total_signed) if move else 0.0

    @api.model
    def _cron_rn_ewb_expiry(self):
        """To-do for the salesperson of the invoice when an e-way bill is about to expire."""
        for ewb in self.search([('rn_ewb_expiring', '=', True)]):
            user = ewb.account_move_id.invoice_user_id
            if not user or ewb.activity_ids.filtered(lambda a: a.user_id == user and a.res_id == ewb.id):
                continue
            ewb.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=ewb.ewaybill_expiry_date,
                summary=_('E-way bill %s expires on %s: extend it or close the delivery',
                          ewb.name or ewb.display_name, ewb.ewaybill_expiry_date),
                user_id=user.id,
            )
