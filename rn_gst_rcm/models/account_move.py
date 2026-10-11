# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')
HEADS = ('igst', 'cgst', 'sgst', 'cess')
# Time of supply of services under reverse charge, section 13(3): the payment date or
# the date immediately following 60 days from the supplier's invoice, if earlier.
SERVICE_DAYS = 61
SELF_INVOICE_DAYS = 30


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_is_rcm = fields.Boolean(
        string='Reverse Charge', compute='_compute_rn_is_rcm', store=True, index=True,
        help='A vendor bill with at least one reverse charge tax.',
    )
    rn_rcm_missing = fields.Boolean(compute='_compute_rn_rcm_missing')
    rn_rcm_missing_note = fields.Char(compute='_compute_rn_rcm_missing')
    rn_rcm_supply_type = fields.Selection([
        ('services', 'Services'),
        ('goods', 'Goods'),
    ], string='RCM Supply', compute='_compute_rn_rcm_dates')
    rn_rcm_tax = fields.Monetary(string='RCM Tax', compute='_compute_rn_rcm_dates', currency_field='company_currency_id')
    rn_rcm_payment_date = fields.Date(string='First Payment', compute='_compute_rn_rcm_dates')
    rn_rcm_tos_date = fields.Date(string='Time of Supply', compute='_compute_rn_rcm_dates',
                                      help='Date the reverse charge tax falls due: the payment date, or the 61st day '
                                           '(services) / 31st day (goods) after the supplier invoice, whichever is earlier.')
    rn_rcm_tos_period = fields.Char(string='Tax Month', compute='_compute_rn_rcm_dates')
    rn_self_invoice_required = fields.Boolean(compute='_compute_rn_self_invoice_required')
    rn_self_invoice_number = fields.Char(string='Self-Invoice Number', copy=False, readonly=True, index=True)
    rn_self_invoice_date = fields.Date(string='Self-Invoice Date', copy=False, readonly=True)
    rn_self_invoice_due = fields.Date(string='Self-Invoice Due', compute='_compute_rn_self_invoice_required')

    @api.depends('move_type', 'invoice_line_ids.tax_ids')
    def _compute_rn_is_rcm(self):
        for move in self:
            move.rn_is_rcm = move.move_type in PURCHASE_TYPES and any(
                tax.l10n_in_reverse_charge for tax in move.invoice_line_ids.tax_ids
            )

    @api.depends('move_type', 'state', 'partner_id', 'invoice_line_ids.product_id',
                 'invoice_line_ids.account_id', 'invoice_line_ids.tax_ids')
    def _compute_rn_rcm_missing(self):
        Rule = self.env['rn.gst.rcm.rule']
        for move in self:
            missing = []
            if move.move_type in PURCHASE_TYPES and move.state == 'draft' and move.country_code == 'IN':
                for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                    if any(tax.l10n_in_reverse_charge for tax in line.tax_ids):
                        continue
                    rule = Rule._rn_rule_for_line(line)
                    if rule:
                        missing.append('%s (%s)' % (line.name or line.product_id.display_name or '', rule.name))
            move.rn_rcm_missing = bool(missing)
            move.rn_rcm_missing_note = ', '.join(missing) or False

    @api.depends('rn_is_rcm', 'invoice_date', 'line_ids.balance', 'line_ids.matched_debit_ids', 'line_ids.matched_credit_ids')
    def _compute_rn_rcm_dates(self):
        for move in self:
            if not move.rn_is_rcm or not move.invoice_date:
                move.rn_rcm_supply_type = move.rn_rcm_payment_date = move.rn_rcm_tos_date = False
                move.rn_rcm_tos_period = False
                move.rn_rcm_tax = 0.0
                continue
            rc_lines = move.invoice_line_ids.filtered(lambda l: any(t.l10n_in_reverse_charge for t in l.tax_ids))
            is_service = any(
                line.product_id.type == 'service'
                or any(tax.tax_scope == 'service' for tax in line.tax_ids.flatten_taxes_hierarchy())
                for line in rc_lines
            )
            # The reverse charge tax owed is the -100% line of each reverse charge tax.
            move.rn_rcm_tax = -sum(move.line_ids.filtered(
                lambda l: l.tax_line_id.l10n_in_reverse_charge and l.tax_repartition_line_id.factor_percent < 0
            ).mapped('balance'))
            payable = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
            # Date of the payment entry itself, not the later of the two matched lines.
            payment_dates = [
                (p.debit_move_id if p.credit_move_id in payable else p.credit_move_id).date
                for p in payable.matched_debit_ids | payable.matched_credit_ids
            ]
            payment_date = min(payment_dates) if payment_dates else False
            if is_service:
                limit = move.invoice_date + timedelta(days=SERVICE_DAYS)
            else:
                # Goods are taken as received on the invoice date, which always comes before the 31st day.
                limit = move.invoice_date
            tos = min(d for d in (payment_date, limit) if d)
            move.rn_rcm_supply_type = 'services' if is_service else 'goods'
            move.rn_rcm_payment_date = payment_date
            move.rn_rcm_tos_date = tos
            move.rn_rcm_tos_period = tos.strftime('%Y-%m')

    @api.depends('rn_is_rcm', 'l10n_in_gst_treatment', 'invoice_date')
    def _compute_rn_self_invoice_required(self):
        for move in self:
            required = (
                move.rn_is_rcm and move.move_type == 'in_invoice'
                and move.l10n_in_gst_treatment in ('unregistered', 'consumer')
            )
            move.rn_self_invoice_required = required
            move.rn_self_invoice_due = (
                move.invoice_date + timedelta(days=SELF_INVOICE_DAYS) if required and move.invoice_date else False
            )

    def action_rn_apply_rcm(self):
        """Put the reverse charge tax of the matching rule on each line that needs it."""
        Rule = self.env['rn.gst.rcm.rule']
        for move in self:
            if move.state != 'draft':
                raise UserError(_('Reverse charge taxes can only be applied on a draft bill.'))
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                if any(tax.l10n_in_reverse_charge for tax in line.tax_ids):
                    continue
                rule = Rule._rn_rule_for_line(line)
                tax = rule and rule._rn_tax_for_move(move)
                if not tax:
                    continue
                line.tax_ids = tax
            move.message_post(body=_('Reverse charge taxes applied from the RCM rules.'))
        return True

    def action_rn_issue_self_invoice(self):
        for move in self:
            if not move.rn_self_invoice_required:
                raise UserError(_('A self-invoice is needed only for reverse charge bills from unregistered suppliers.'))
            if move.state != 'posted':
                raise UserError(_('Post the bill before issuing its self-invoice.'))
            if move.rn_self_invoice_number:
                continue
            today = fields.Date.context_today(move)
            move.write({
                'rn_self_invoice_number': self.env['ir.sequence'].with_company(move.company_id).next_by_code(
                    'rn.gst.rcm.self.invoice', sequence_date=today,
                ),
                'rn_self_invoice_date': today,
            })
            body = _('Self-invoice %s issued.', move.rn_self_invoice_number)
            if move.rn_self_invoice_due and today > move.rn_self_invoice_due:
                body += ' ' + _('It is late: it was due by %s.', move.rn_self_invoice_due)
            move.message_post(body=body)
        return self.env.ref('rn_gst_rcm.rn_gst_rcm_action_report_self_invoice').report_action(self)

    def _rn_self_invoice_taxes(self):
        """Reverse charge tax of the bill by head, for the self-invoice print."""
        self.ensure_one()
        amounts = dict.fromkeys(HEADS, 0.0)
        for line in self.line_ids.filtered(
            lambda l: l.tax_line_id.l10n_in_reverse_charge and l.tax_repartition_line_id.factor_percent < 0
        ):
            head = line.tax_line_id.l10n_in_gst_tax_type
            if head:
                amounts[head] -= line.balance
        return amounts
