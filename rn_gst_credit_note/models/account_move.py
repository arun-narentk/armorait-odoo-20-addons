# -*- coding: utf-8 -*-
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

CREDIT_NOTE_TYPES = ('out_refund', 'in_refund')


def _section34_deadline(invoice_date):
    """Last day to reduce GST by a credit note: 30 November after the end of the
    financial year (April to March) of the original invoice (section 34(2))."""
    fy_start = invoice_date.year if invoice_date.month >= 4 else invoice_date.year - 1
    return date(fy_start + 1, 11, 30)


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_cn_reason_id = fields.Many2one(
        'rn.gst.credit.note.reason', string='Credit Note Reason', tracking=True, index='btree_not_null',
    )
    rn_cn_deadline = fields.Date(
        string='GST Credit Note Deadline', compute='_compute_rn_cn_checks', store=True,
        help='30 November after the end of the financial year of the original invoice.',
    )
    rn_cn_check_state = fields.Selection([
        ('ok', 'No Issues'),
        ('warning', 'Warnings'),
        ('error', 'Errors'),
    ], string='Credit Note Check', compute='_compute_rn_cn_checks', store=True, index='btree_not_null')
    rn_cn_check_messages = fields.Text(string='Credit Note Issues', compute='_compute_rn_cn_checks', store=True)
    rn_cn_credited_amount = fields.Monetary(
        string='Credited', compute='_compute_rn_cn_credited', currency_field='currency_id',
        help='Taxable value of the posted credit notes of this invoice.',
    )
    rn_cn_remaining_amount = fields.Monetary(
        string='Left to Credit', compute='_compute_rn_cn_credited', currency_field='currency_id',
    )

    @api.depends('reversal_move_ids.state', 'reversal_move_ids.amount_untaxed', 'amount_untaxed')
    def _compute_rn_cn_credited(self):
        for move in self:
            credited = sum(move.reversal_move_ids.filtered(lambda m: m.state == 'posted').mapped('amount_untaxed'))
            move.rn_cn_credited_amount = credited
            move.rn_cn_remaining_amount = move.amount_untaxed - credited if move.is_invoice() else 0.0

    @api.model
    def _rn_cn_gst_taxes(self, move):
        taxes = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product').tax_ids
        return taxes.flatten_taxes_hierarchy().filtered('l10n_in_gst_tax_type')

    @api.depends(
        'move_type', 'country_code', 'rn_cn_reason_id', 'invoice_date', 'date', 'commercial_partner_id',
        'amount_untaxed', 'invoice_line_ids.tax_ids', 'l10n_in_state_id',
        'reversed_entry_id.state', 'reversed_entry_id.invoice_date', 'reversed_entry_id.amount_untaxed',
        'reversed_entry_id.commercial_partner_id', 'reversed_entry_id.l10n_in_state_id',
        'reversed_entry_id.reversal_move_ids.state', 'reversed_entry_id.reversal_move_ids.amount_untaxed',
    )
    def _compute_rn_cn_checks(self):
        for move in self:
            move.rn_cn_deadline = False
            move.rn_cn_check_state = False
            move.rn_cn_check_messages = False
            if move.move_type not in CREDIT_NOTE_TYPES or move.country_code != 'IN':
                continue
            errors, warnings = move._rn_cn_findings()
            move.rn_cn_check_state = 'error' if errors else 'warning' if warnings else 'ok'
            move.rn_cn_check_messages = '\n'.join(
                [_('Error: %s', e) for e in errors] + [_('Warning: %s', w) for w in warnings]
            ) or False

    def _rn_cn_findings(self):
        """(errors, warnings) of a credit note, as plain sentences."""
        self.ensure_one()
        errors, warnings = [], []
        reason = self.rn_cn_reason_id
        original = self.reversed_entry_id
        gst_taxes = self._rn_cn_gst_taxes(self)
        if not reason:
            warnings.append(_('No credit note reason. GSTR-1 needs to know why the value is reduced.'))
        if reason and not reason.gst_credit:
            if gst_taxes:
                errors.append(_(
                    'A financial credit note must not carry GST: the supplier\'s tax does not change. '
                    'Remove the GST taxes or pick a GST reason.'
                ))
            return errors, warnings
        if not original:
            message = _('Link the original invoice. A GST credit note must refer to the invoice it reduces.')
            (errors if reason.requires_original else warnings).append(message)
            return errors, warnings
        if original.state != 'posted':
            errors.append(_('The original invoice %s is not posted.', original.display_name))
        if original.commercial_partner_id != self.commercial_partner_id:
            errors.append(_(
                'The original invoice %(invoice)s is for %(partner)s, not for this partner.',
                invoice=original.display_name, partner=original.commercial_partner_id.display_name,
            ))
        if original.invoice_date:
            deadline = _section34_deadline(original.invoice_date)
            self.rn_cn_deadline = deadline
            note_date = self.invoice_date or self.date or fields.Date.context_today(self)
            if note_date > deadline:
                errors.append(_(
                    'Dated %(date)s, after the section 34 time limit of %(deadline)s for invoice %(invoice)s. '
                    'GST can no longer be reduced: issue a financial credit note without GST.',
                    date=note_date, deadline=deadline, invoice=original.display_name,
                ))
        others = original.reversal_move_ids.filtered(lambda m: m.state == 'posted' and m != self)
        credited = sum(others.mapped('amount_untaxed')) + self.amount_untaxed
        if self.currency_id.compare_amounts(credited, original.amount_untaxed) > 0:
            errors.append(_(
                'Credit notes on %(invoice)s add up to %(credited)s, more than its taxable value of %(total)s.',
                invoice=original.display_name,
                credited=self.currency_id.format(credited), total=self.currency_id.format(original.amount_untaxed),
            ))
        original_taxes = self._rn_cn_gst_taxes(original)
        extra_rates = set(gst_taxes.mapped('amount')) - set(original_taxes.mapped('amount'))
        if extra_rates:
            errors.append(_(
                'GST rate %(rates)s%% is not on the original invoice. A credit note must use the rates of the invoice.',
                rates=', '.join('%g' % r for r in sorted(extra_rates)),
            ))
        if gst_taxes and original_taxes and (
            ('igst' in gst_taxes.mapped('l10n_in_gst_tax_type')) != ('igst' in original_taxes.mapped('l10n_in_gst_tax_type'))
        ):
            errors.append(_('The original invoice and the credit note differ in IGST against CGST/SGST.'))
        if self.l10n_in_state_id and original.l10n_in_state_id and self.l10n_in_state_id != original.l10n_in_state_id:
            warnings.append(_(
                'Place of supply %(note)s differs from the original invoice (%(invoice)s).',
                note=self.l10n_in_state_id.name, invoice=original.l10n_in_state_id.name,
            ))
        return errors, warnings

    def _post(self, soft=True):
        blocked = self.filtered(
            lambda m: m.move_type in CREDIT_NOTE_TYPES and m.company_id.rn_gst_cn_block_on_error
            and m.rn_cn_check_state == 'error'
        )
        if blocked:
            raise UserError(_(
                'These credit notes have GST errors and cannot be posted:\n%s',
                '\n\n'.join('%s\n%s' % (m.display_name, m.rn_cn_check_messages) for m in blocked),
            ))
        return super()._post(soft)
