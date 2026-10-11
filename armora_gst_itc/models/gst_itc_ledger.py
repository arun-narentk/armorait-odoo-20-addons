# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

HEADS = ('igst', 'cgst', 'sgst', 'cess')
PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')
SALE_TYPES = ('out_invoice', 'out_refund', 'out_receipt')
EXEMPT_SALE_SECTIONS = ('sale_nil_rated', 'sale_exempt', 'sale_non_gst_supplies')
RULE37_DAYS = 180
INTEREST_RATE = 0.18


class ArmoraGstItcBill(models.Model):
    """ITC register: one line per vendor bill of the month."""

    _name = 'armora.gst.itc.bill'
    _description = 'ITC Register Line'
    _order = 'invoice_date, id'

    ledger_id = fields.Many2one('armora.gst.itc.ledger', string='ITC Ledger', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='ledger_id.company_id', store=True)
    currency_id = fields.Many2one(related='ledger_id.currency_id')
    move_id = fields.Many2one('account.move', string='Vendor Bill', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='move_id.partner_id', store=True)
    vendor_gstin = fields.Char(related='move_id.partner_id.vat', string='Vendor GSTIN')
    invoice_date = fields.Date(related='move_id.invoice_date', store=True)
    bill_total = fields.Monetary(currency_field='currency_id')
    paid_amount = fields.Monetary(string='Paid by Month End', currency_field='currency_id')
    itc_total = fields.Monetary(string='ITC', currency_field='currency_id')
    blocked_total = fields.Monetary(string='Blocked', currency_field='currency_id')
    common_total = fields.Monetary(string='Common Credit', currency_field='currency_id')
    gstr2b_status = fields.Selection([
        ('matched', 'In 2B, matched'),
        ('mismatch', 'In 2B, mismatch'),
        ('not_in_2b', 'Not in 2B'),
        ('unknown', 'No 2B data'),
    ], string='GSTR-2B', default='unknown')


class ArmoraGstItcLedger(models.Model):
    _name = 'armora.gst.itc.ledger'
    _description = 'ITC Ledger'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_start desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    gstin = fields.Char(required=True, tracking=True, index=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    return_period = fields.Char(required=True, tracking=True, help='Month MM, e.g. 04 for April.')
    period_start = fields.Date(compute='_compute_period', store=True)
    period_end = fields.Date(compute='_compute_period', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('locked', 'Locked'),
    ], default='draft', required=True, tracking=True, copy=False)
    bill_ids = fields.One2many('armora.gst.itc.bill', 'ledger_id', string='ITC Register')
    entry_ids = fields.One2many('armora.gst.itc.entry', 'ledger_id', string='Reversals and Reclaims')

    availed_igst = fields.Monetary(string='Availed IGST', currency_field='currency_id', readonly=True)
    availed_cgst = fields.Monetary(string='Availed CGST', currency_field='currency_id', readonly=True)
    availed_sgst = fields.Monetary(string='Availed SGST', currency_field='currency_id', readonly=True)
    availed_cess = fields.Monetary(string='Availed Cess', currency_field='currency_id', readonly=True)

    blocked_igst = fields.Monetary(string='Blocked 17(5) IGST', currency_field='currency_id', readonly=True)
    blocked_cgst = fields.Monetary(string='Blocked 17(5) CGST', currency_field='currency_id', readonly=True)
    blocked_sgst = fields.Monetary(string='Blocked 17(5) SGST', currency_field='currency_id', readonly=True)
    blocked_cess = fields.Monetary(string='Blocked 17(5) Cess', currency_field='currency_id', readonly=True)

    common_igst = fields.Monetary(string='Common Credit IGST', currency_field='currency_id', readonly=True)
    common_cgst = fields.Monetary(string='Common Credit CGST', currency_field='currency_id', readonly=True)
    common_sgst = fields.Monetary(string='Common Credit SGST', currency_field='currency_id', readonly=True)
    common_cess = fields.Monetary(string='Common Credit Cess', currency_field='currency_id', readonly=True)

    rule42_igst = fields.Monetary(string='Rule 42 Reversal IGST', currency_field='currency_id', readonly=True)
    rule42_cgst = fields.Monetary(string='Rule 42 Reversal CGST', currency_field='currency_id', readonly=True)
    rule42_sgst = fields.Monetary(string='Rule 42 Reversal SGST', currency_field='currency_id', readonly=True)
    rule42_cess = fields.Monetary(string='Rule 42 Reversal Cess', currency_field='currency_id', readonly=True)

    rule37_igst = fields.Monetary(string='Rule 37 Reversal IGST', currency_field='currency_id', readonly=True)
    rule37_cgst = fields.Monetary(string='Rule 37 Reversal CGST', currency_field='currency_id', readonly=True)
    rule37_sgst = fields.Monetary(string='Rule 37 Reversal SGST', currency_field='currency_id', readonly=True)
    rule37_cess = fields.Monetary(string='Rule 37 Reversal Cess', currency_field='currency_id', readonly=True)

    reclaimed_igst = fields.Monetary(string='Reclaimed IGST', currency_field='currency_id', readonly=True)
    reclaimed_cgst = fields.Monetary(string='Reclaimed CGST', currency_field='currency_id', readonly=True)
    reclaimed_sgst = fields.Monetary(string='Reclaimed SGST', currency_field='currency_id', readonly=True)
    reclaimed_cess = fields.Monetary(string='Reclaimed Cess', currency_field='currency_id', readonly=True)

    net_igst = fields.Monetary(string='Net ITC IGST', currency_field='currency_id', readonly=True)
    net_cgst = fields.Monetary(string='Net ITC CGST', currency_field='currency_id', readonly=True)
    net_sgst = fields.Monetary(string='Net ITC SGST', currency_field='currency_id', readonly=True)
    net_cess = fields.Monetary(string='Net ITC Cess', currency_field='currency_id', readonly=True)

    opening_manual_igst = fields.Monetary(string='Opening Balance IGST', currency_field='currency_id')
    opening_manual_cgst = fields.Monetary(string='Opening Balance CGST', currency_field='currency_id')
    opening_manual_sgst = fields.Monetary(string='Opening Balance SGST', currency_field='currency_id')
    opening_manual_cess = fields.Monetary(string='Opening Balance Cess', currency_field='currency_id')

    opening_igst = fields.Monetary(string='Opening IGST', currency_field='currency_id', compute='_compute_credit_ledger')
    opening_cgst = fields.Monetary(string='Opening CGST', currency_field='currency_id', compute='_compute_credit_ledger')
    opening_sgst = fields.Monetary(string='Opening SGST', currency_field='currency_id', compute='_compute_credit_ledger')
    opening_cess = fields.Monetary(string='Opening Cess', currency_field='currency_id', compute='_compute_credit_ledger')

    utilized_igst = fields.Monetary(string='Used in GSTR-3B IGST', currency_field='currency_id', compute='_compute_credit_ledger')
    utilized_cgst = fields.Monetary(string='Used in GSTR-3B CGST', currency_field='currency_id', compute='_compute_credit_ledger')
    utilized_sgst = fields.Monetary(string='Used in GSTR-3B SGST', currency_field='currency_id', compute='_compute_credit_ledger')
    utilized_cess = fields.Monetary(string='Used in GSTR-3B Cess', currency_field='currency_id', compute='_compute_credit_ledger')

    closing_igst = fields.Monetary(string='Closing IGST', currency_field='currency_id', compute='_compute_credit_ledger')
    closing_cgst = fields.Monetary(string='Closing CGST', currency_field='currency_id', compute='_compute_credit_ledger')
    closing_sgst = fields.Monetary(string='Closing SGST', currency_field='currency_id', compute='_compute_credit_ledger')
    closing_cess = fields.Monetary(string='Closing Cess', currency_field='currency_id', compute='_compute_credit_ledger')

    turnover_exempt = fields.Monetary(string='Exempt Turnover', currency_field='currency_id', readonly=True)
    turnover_total = fields.Monetary(string='Total Turnover', currency_field='currency_id', readonly=True)
    rule42_ratio = fields.Float(string='Exempt Share %', digits=(16, 2), readonly=True)
    interest_total = fields.Monetary(string='Rule 37 Interest', currency_field='currency_id', readonly=True)
    previous_ledger_id = fields.Many2one('armora.gst.itc.ledger', compute='_compute_credit_ledger')
    computed_at = fields.Datetime(readonly=True, copy=False)
    notes = fields.Text()

    _armora_gst_itc_ledger_uniq = models.Constraint(
        'unique(company_id, gstin, financial_year, return_period)',
        "An ITC ledger already exists for this company, GSTIN and month.",
    )

    @api.depends('financial_year', 'return_period')
    def _compute_period(self):
        Period = self.env['armora.gst.period']
        for rec in self:
            try:
                rec.period_start, rec.period_end = Period.compute_period_dates(
                    rec.financial_year, rec.return_period, 'monthly',
                ) if rec.financial_year and rec.return_period else (False, False)
            except ValidationError:
                rec.period_start = rec.period_end = False

    @api.depends('period_start', 'opening_manual_igst', 'opening_manual_cgst', 'opening_manual_sgst',
                 'opening_manual_cess', *['net_%s' % h for h in HEADS])
    def _compute_credit_ledger(self):
        """Electronic credit ledger: opening (last month's closing), plus net ITC,
        minus the credit used in this month's GSTR-3B."""
        for rec in self:
            previous = rec._armora_previous_ledger()
            used = rec._armora_gstr3b_utilization()
            rec.previous_ledger_id = previous
            for head in HEADS:
                opening = previous['closing_%s' % head] if previous else rec['opening_manual_%s' % head]
                rec['opening_%s' % head] = opening
                rec['utilized_%s' % head] = used.get(head, 0.0)
                rec['closing_%s' % head] = opening + rec['net_%s' % head] - used.get(head, 0.0)

    def _armora_previous_ledger(self):
        self.ensure_one()
        if not self.period_start or not self.company_id:
            return self.browse()
        return self.search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('period_end', '<', self.period_start),
            ('state', '!=', 'draft'),
        ], order='period_end desc', limit=1)

    def _armora_gstr3b_utilization(self):
        self.ensure_one()
        if 'armora.gst.3b' not in self.env or not self.financial_year:
            return {}
        gstr3b = self.env['armora.gst.3b'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
            ('state', 'in', ('computed', 'filed')),
        ], limit=1)
        return {head: gstr3b['itc_utilized_%s' % head] for head in HEADS} if gstr3b else {}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('armora.gst.itc.ledger') or _('New')
            if not vals.get('gstin'):
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                vals['gstin'] = company.vat or ''
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(lambda r: r.state == 'locked') and set(vals) - {
            'state', 'notes', 'message_follower_ids', 'activity_ids', 'message_ids',
        } and not self.env.su:
            raise UserError(_('A locked ITC ledger is read-only. Unlock it first.'))
        return super().write(vals)

    def action_lock(self):
        self.write({'state': 'locked'})
        return True

    def action_unlock(self):
        self.write({'state': 'computed'})
        return True

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    def action_compute(self):
        for rec in self:
            if rec.state == 'locked':
                raise UserError(_('A locked ITC ledger is read-only. Unlock it first.'))
            later = self.search([
                ('company_id', '=', rec.company_id.id), ('gstin', '=', rec.gstin),
                ('period_start', '>', rec.period_start), ('state', '!=', 'draft'),
            ], limit=1)
            if later.entry_ids.filtered(lambda e: e.reversal_id.ledger_id == rec):
                raise UserError(_(
                    'Ledger %s reclaims reversals of this month. Reset it to draft before computing this month again.',
                    later.name,
                ))
            rec.entry_ids.unlink()
            rec.bill_ids.unlink()
            vals = defaultdict(float)
            bills = rec._armora_compute_bills(vals)
            entries = rec._armora_compute_rule37() + rec._armora_compute_reclaims()
            for entry in entries:
                prefix = 'rule37' if entry['entry_type'] == 'rule37' else 'reclaimed'
                for head in HEADS:
                    vals['%s_%s' % (prefix, head)] += entry[head]
                vals['interest_total'] += entry.get('interest', 0.0)
            currency = rec.currency_id
            write_vals = {name: currency.round(amount) for name, amount in vals.items()}
            for head in HEADS:
                write_vals['net_%s' % head] = currency.round(
                    vals['availed_%s' % head] + vals['reclaimed_%s' % head]
                    - vals['blocked_%s' % head] - vals['rule42_%s' % head] - vals['rule37_%s' % head]
                )
            write_vals.update({
                'bill_ids': [Command.create(bill) for bill in bills],
                'entry_ids': [Command.create(entry) for entry in entries],
                'state': 'computed',
                'computed_at': fields.Datetime.now(),
            })
            rec.write(write_vals)
            rec.message_post(body=_(
                'ITC ledger computed: %(bills)s bills, net ITC %(net)s, Rule 37 reversals %(r37)s, reclaims %(rec)s.',
                bills=len(bills), net=sum(rec['net_%s' % h] for h in HEADS),
                r37=sum(rec['rule37_%s' % h] for h in HEADS), rec=sum(rec['reclaimed_%s' % h] for h in HEADS),
            ))
        return True

    def _armora_line_domain(self, move_types, date_from, date_to):
        self.ensure_one()
        return [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('move_id.move_type', 'in', move_types),
        ]

    def _armora_itc_by_move(self, date_from, date_to, move_types=PURCHASE_TYPES):
        """GST input tax per bill and head: the +100% GST tax lines, reverse charge credit included."""
        itc = defaultdict(lambda: dict.fromkeys(HEADS, 0.0))
        for move, tax, balance in self.env['account.move.line']._read_group(
            self._armora_line_domain(move_types, date_from, date_to) + [
                ('display_type', '=', 'tax'),
                ('tax_repartition_line_id.factor_percent', '>', 0),
            ],
            ['move_id', 'tax_line_id'], ['balance:sum'],
        ):
            head = tax.l10n_in_gst_tax_type
            if head:
                itc[move][head] += balance
        return itc

    @api.model
    def _armora_treatment_shares(self, move):
        """Share of the bill's value per ITC type of its lines."""
        lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        shares = defaultdict(float)
        for line in lines:
            shares[line.armora_itc_treatment or 'eligible'] += abs(line.balance)
        total = sum(shares.values())
        if not total:
            return {'eligible': 1.0}
        return {treatment: amount / total for treatment, amount in shares.items()}

    @api.model
    def _armora_paid_amount(self, move, on_date):
        """Amount of the bill paid (reconciled) on or before a date, in company currency."""
        payable = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
        paid = 0.0
        for partial in payable.matched_debit_ids | payable.matched_credit_ids:
            # Date of the payment entry itself, not the later of the two matched lines.
            counterpart = partial.debit_move_id if partial.credit_move_id in payable else partial.credit_move_id
            if counterpart.date <= on_date:
                paid += partial.amount
        return paid

    def _armora_gstr2b_status(self, moves):
        if 'armora.gst.gstr2b.line' not in self.env:
            return {}
        lines = self.env['armora.gst.gstr2b.line'].sudo().search([
            ('move_id', 'in', moves.ids), ('source', '=', 'gstr2b'),
            ('match_state', 'in', ('matched', 'mismatch')),
        ])
        status = {line.move_id.id: line.match_state for line in lines}
        has_2b = bool(self.env['armora.gst.gstr2b'].sudo().search_count([
            ('company_id', '=', self.company_id.id),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
            ('state', '!=', 'cancelled'),
        ]))
        return {move.id: status.get(move.id, 'not_in_2b' if has_2b else 'unknown') for move in moves}

    def _armora_compute_bills(self, vals):
        self.ensure_one()
        itc = self._armora_itc_by_move(self.period_start, self.period_end)
        moves = self.env['account.move'].browse([move.id for move in itc])
        status = self._armora_gstr2b_status(moves)
        common = dict.fromkeys(HEADS, 0.0)
        bills = []
        for move in moves:
            heads = itc[move]
            shares = self._armora_treatment_shares(move)
            for head, amount in heads.items():
                vals['availed_%s' % head] += amount
                vals['blocked_%s' % head] += amount * shares.get('blocked', 0.0)
                common[head] += amount * shares.get('common', 0.0)
            total_itc = sum(heads.values())
            bills.append({
                'move_id': move.id,
                'bill_total': abs(move.amount_total_signed),
                'paid_amount': self._armora_paid_amount(move, self.period_end),
                'itc_total': total_itc,
                'blocked_total': total_itc * shares.get('blocked', 0.0),
                'common_total': total_itc * shares.get('common', 0.0),
                'gstr2b_status': status.get(move.id, 'unknown'),
            })
        # Rule 42: common credit reversed in the ratio of exempt to total turnover of the month.
        exempt = total = 0.0
        for section, balance in self.env['account.move.line']._read_group(
            self._armora_line_domain(SALE_TYPES, self.period_start, self.period_end) + [
                ('display_type', '=', 'product'),
                ('l10n_in_gstr_section', 'not in', (False, 'sale_out_of_scope')),
            ],
            ['l10n_in_gstr_section'], ['balance:sum'],
        ):
            total -= balance
            if section in EXEMPT_SALE_SECTIONS:
                exempt -= balance
        ratio = exempt / total if total else 0.0
        vals['turnover_exempt'] = exempt
        vals['turnover_total'] = total
        vals['rule42_ratio'] = ratio * 100.0
        for head in HEADS:
            vals['common_%s' % head] = common[head]
            vals['rule42_%s' % head] = common[head] * ratio
        return bills

    def _armora_compute_rule37(self):
        """Bills whose 180th day falls in this month and that were not fully paid by then."""
        self.ensure_one()
        date_from = self.period_start - timedelta(days=RULE37_DAYS)
        date_to = self.period_end - timedelta(days=RULE37_DAYS)
        itc = self._armora_itc_by_move(date_from, date_to, ('in_invoice',))
        reversed_moves = self.env['armora.gst.itc.entry'].search([
            ('company_id', '=', self.company_id.id), ('gstin', '=', self.gstin),
            ('entry_type', '=', 'rule37'), ('move_id', 'in', [m.id for m in itc]),
        ]).move_id
        entries = []
        for move, heads in itc.items():
            if move in reversed_moves:
                continue
            day180 = move.invoice_date + timedelta(days=RULE37_DAYS)
            bill_total = abs(move.amount_total_signed)
            unpaid = bill_total - self._armora_paid_amount(move, day180)
            if not bill_total or move.currency_id.compare_amounts(unpaid, 0.0) <= 0:
                continue
            shares = self._armora_treatment_shares(move)
            # Blocked credit is already reversed in full; reverse the rest in the unpaid share.
            factor = (1.0 - shares.get('blocked', 0.0)) * unpaid / bill_total
            reversal = {head: amount * factor for head, amount in heads.items()}
            availed_on = (move.invoice_date + relativedelta(months=1)).replace(day=20)
            days = max((self.period_end - availed_on).days, 0)
            entries.append({
                'entry_type': 'rule37',
                'move_id': move.id,
                'reversal_date': self.period_end,
                'bill_total': bill_total,
                'unpaid_amount': unpaid,
                'interest': sum(reversal.values()) * INTEREST_RATE * days / 365.0,
                **reversal,
            })
        return entries

    def _armora_compute_reclaims(self):
        """Give back Rule 37 reversals of earlier months in proportion to what has been paid since."""
        self.ensure_one()
        open_reversals = self.env['armora.gst.itc.entry'].search([
            ('company_id', '=', self.company_id.id), ('gstin', '=', self.gstin),
            ('entry_type', '=', 'rule37'), ('reversal_date', '<', self.period_start),
        ])
        entries = []
        for reversal in open_reversals:
            remaining = reversal._remaining()
            if not any(remaining.values()) or not reversal.unpaid_amount:
                continue
            unpaid_now = max(reversal.bill_total - self._armora_paid_amount(reversal.move_id, self.period_end), 0.0)
            keep = min(unpaid_now / reversal.unpaid_amount, 1.0)
            reclaim = {head: remaining[head] - reversal[head] * keep for head in HEADS}
            if reversal.currency_id.compare_amounts(sum(reclaim.values()), 0.0) <= 0:
                continue
            entries.append({
                'entry_type': 'reclaim',
                'move_id': reversal.move_id.id,
                'reversal_id': reversal.id,
                'reversal_date': self.period_end,
                'bill_total': reversal.bill_total,
                'unpaid_amount': unpaid_now,
                **reclaim,
            })
        return entries
