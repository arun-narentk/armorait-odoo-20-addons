# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import date

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from .gstr9c_rows import ROWS, TOTAL_ORDER, TOTALS

HEADS = ('igst', 'cgst', 'sgst', 'cess')
KIND_FIELDS = {
    'tax': ('value',) + HEADS,
    'value': ('value',),
    'itc': HEADS,
}
# Outward supplies on which the supplier pays tax (GSTR-9 Tables 4A to 4E, 4I, 4J).
TAXABLE_SALE_SECTIONS = (
    'sale_b2cl', 'sale_b2cs', 'sale_b2b_regular', 'sale_exp_wp', 'sale_sez_wp', 'sale_deemed_export',
    'sale_cdnr_regular', 'sale_cdnr_deemed_export', 'sale_cdnr_sez_wp', 'sale_cdnur_b2cl', 'sale_cdnur_exp_wp',
)
RCM_INWARD_SECTIONS = (
    'purchase_b2b_rcm', 'purchase_b2c_rcm', 'purchase_imp_services', 'purchase_cdnr_rcm', 'purchase_cdnur_rcm',
)
PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')


class ArmoraGstGstr9c(models.Model):
    _name = 'armora.gst.gstr9c'
    _description = 'GSTR-9C Reconciliation Statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'financial_year desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    gstin = fields.Char(required=True, tracking=True, index=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    date_from = fields.Date(compute='_compute_dates', store=True)
    date_to = fields.Date(compute='_compute_dates', store=True)
    gstr9_id = fields.Many2one(
        'armora.gst.gstr9', string='GSTR-9',
        domain="[('company_id', '=', company_id), ('financial_year', '=', financial_year)]",
        help='Annual return this statement reconciles with. Found automatically when left empty.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Filled'),
        ('filed', 'Filed'),
    ], default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('armora.gst.gstr9c.line', 'gstr9c_id', string='Rows')
    part2_line_ids = fields.One2many('armora.gst.gstr9c.line', 'gstr9c_id', domain=[('part', '=', '2')])
    part3_line_ids = fields.One2many('armora.gst.gstr9c.line', 'gstr9c_id', domain=[('part', '=', '3')])
    part4_line_ids = fields.One2many('armora.gst.gstr9c.line', 'gstr9c_id', domain=[('part', '=', '4')])
    rate_ids = fields.One2many('armora.gst.gstr9c.rate', 'gstr9c_id', string='Rate-wise Liability')
    expense_ids = fields.One2many('armora.gst.gstr9c.expense', 'gstr9c_id', string='Expense-wise ITC')
    reason_turnover = fields.Text(string='Reasons for unreconciled turnover (Table 6)')
    reason_taxable = fields.Text(string='Reasons for unreconciled taxable turnover (Table 8)')
    reason_tax = fields.Text(string='Reasons for unpaid tax (Table 10)')
    reason_itc = fields.Text(string='Reasons for unreconciled ITC (Table 13)')
    reason_expense_itc = fields.Text(string='Reasons for unreconciled ITC on expenses (Table 15)')
    filled_at = fields.Datetime(string='Filled from Books On', readonly=True, copy=False)
    fill_warning = fields.Text(string='Warnings', readonly=True, copy=False)

    _armora_gst_gstr9c_uniq = models.Constraint(
        'unique(company_id, gstin, financial_year)',
        "A GSTR-9C already exists for this company, GSTIN and financial year.",
    )

    @api.depends('financial_year')
    def _compute_dates(self):
        Period = self.env['armora.gst.period']
        for rec in self:
            if not rec.financial_year:
                rec.date_from = rec.date_to = False
                continue
            start_year = Period.fy_start_year(rec.financial_year)
            rec.date_from = date(start_year, 4, 1)
            rec.date_to = date(start_year + 1, 3, 31)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('armora.gst.gstr9c') or _('New')
            if not vals.get('gstin'):
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                vals['gstin'] = company.vat or ''
            vals.setdefault('line_ids', [
                Command.create({
                    'sequence': index, 'code': code, 'part': part, 'table': table,
                    'label': label, 'kind': kind, 'source': source,
                })
                for index, (code, part, table, label, kind, source) in enumerate(ROWS)
            ])
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(lambda r: r.state == 'filed') and set(vals) - {
            'state', 'message_follower_ids', 'activity_ids', 'message_ids',
        } and not self.env.su:
            raise UserError(_('A filed GSTR-9C is read-only. Reset it to draft first.'))
        return super().write(vals)

    def action_mark_filed(self):
        self.write({'state': 'filed'})
        for rec in self:
            rec.message_post(body=_('GSTR-9C marked as filed.'))
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True

    def _armora_row(self, code):
        self.ensure_one()
        return self.line_ids.filtered(lambda l: l.code == code)[:1]

    def action_fill_from_books(self):
        """Fill the turnover, tax and ITC sides from the ledger and the year's GSTR-9.
        Manual adjustments, reasons and hand-entered rows are kept."""
        for rec in self:
            if rec.state == 'filed':
                raise UserError(_('A filed GSTR-9C is read-only. Reset it to draft first.'))
            warnings = []
            gstr9 = rec.gstr9_id or self.env['armora.gst.gstr9'].search([
                ('company_id', '=', rec.company_id.id),
                ('gstin', '=', rec.gstin),
                ('financial_year', '=', rec.financial_year),
            ], limit=1)
            amounts = defaultdict(lambda: defaultdict(float))
            rec._armora_books_amounts(amounts)
            if gstr9:
                if gstr9.state == 'draft':
                    warnings.append(_('GSTR-9 %s is not filled yet: press Fill from Books on it first.', gstr9.name))
                rec._armora_gstr9_amounts(gstr9, amounts)
            else:
                warnings.append(_('No GSTR-9 found for %s: the annual return side is zero.', rec.financial_year))
            rates = rec._armora_rate_lines()
            expenses = rec._armora_expense_lines()
            amounts['14R']['value'] = sum(line['itc_amount'] for line in expenses)
            currency = rec.currency_id
            for line in rec.line_ids.filtered(lambda l: l.source in ('books', 'gstr9')):
                row = amounts.get(line.code, {})
                line.with_context(armora_gstr9c_totals=True).write({
                    name: currency.round(row.get(name, 0.0)) for name in KIND_FIELDS[line.kind]
                })
            rec.rate_ids.unlink()
            rec.expense_ids.unlink()
            rec.write({
                'gstr9_id': gstr9.id or False,
                'rate_ids': [Command.create(vals) for vals in rates],
                'expense_ids': [Command.create(vals) for vals in expenses],
                'filled_at': fields.Datetime.now(),
                'fill_warning': '\n'.join(warnings) or False,
                'state': 'computed',
            })
            rec._armora_recompute_totals()
            rec.message_post(body=_(
                'GSTR-9C filled. Unreconciled turnover %(turnover)s, unreconciled ITC %(itc)s.',
                turnover=rec._armora_row('5R').value, itc=rec._armora_row('12F').value,
            ))
        return True

    def _armora_recompute_totals(self):
        for rec in self:
            by_code = {line.code: line for line in rec.line_ids}
            values = {code: {name: line[name] for name in KIND_FIELDS[line.kind]} for code, line in by_code.items()}
            for code in TOTAL_ORDER:
                line = by_code.get(code)
                if not line:
                    continue
                total = {
                    name: sum(sign * values.get(src, {}).get(name, 0.0) for sign, src in TOTALS[code])
                    for name in KIND_FIELDS[line.kind]
                }
                if code == '9N':
                    total['value'] += sum(rec.rate_ids.mapped('taxable_value'))
                    for head in HEADS:
                        total[head] += sum(rec.rate_ids.mapped(head))
                values[code] = total
                line.with_context(armora_gstr9c_totals=True).write(total)

    def _armora_ledger_domain(self, move_types=None):
        # The financial statements follow the accounting date.
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if move_types:
            domain.append(('move_id.move_type', 'in', move_types))
        return domain

    def _armora_books_amounts(self, amounts):
        Line = self.env['account.move.line']
        # 5A: revenue from operations, the income accounts of the profit and loss.
        income = Line._read_group(
            self._armora_ledger_domain() + [('account_id.account_type', '=', 'income')], [], ['balance:sum'],
        )[0][0] or 0.0
        amounts['5A']['value'] = -income
        # 12A: input tax booked on bills (+100% GST tax lines, including reverse charge credit).
        amounts['12A']['value'] = sum(self._armora_input_tax_by_move().values())

    def _armora_gstr9_amounts(self, gstr9, amounts):
        row = gstr9._armora_row
        amounts['5Q']['value'] = row('5N').value
        amounts['7B']['value'] = row('5D').value + row('5E').value + row('5F').value
        amounts['7C']['value'] = row('5A').value + row('5B').value
        amounts['7D']['value'] = row('5C').value
        amounts['7F']['value'] = row('4N').value - row('4G').value
        for head in HEADS:
            paid = row('9%s' % head.upper())
            amounts['9O'][head] = paid.cash + sum(paid[credit] for credit in HEADS)
        net_itc = sum(row('7J')[head] for head in HEADS)
        amounts['12E']['value'] = net_itc
        amounts['14S']['value'] = net_itc

    def _armora_input_tax_by_move(self):
        """GST input tax booked per bill: its +100% tax lines, reverse charge credit included."""
        self.ensure_one()
        itc_by_move = defaultdict(float)
        for move, tax, balance in self.env['account.move.line']._read_group(
            self._armora_ledger_domain(PURCHASE_TYPES) + [
                ('display_type', '=', 'tax'),
                ('tax_repartition_line_id.factor_percent', '>', 0),
            ], ['move_id', 'tax_line_id'], ['balance:sum'],
        ):
            if tax.l10n_in_gst_tax_type:
                itc_by_move[move.id] += balance
        return itc_by_move

    def _armora_rate_lines(self):
        """Table 9: liability as per books by tax rate, outward supplies and reverse charge inward."""
        self.ensure_one()
        Extractor = self.env['armora.gst.data.extractor']
        lines = self.env['account.move.line'].search(self._armora_ledger_domain() + [
            ('display_type', '=', 'product'),
            ('l10n_in_gstr_section', 'in', TAXABLE_SALE_SECTIONS + RCM_INWARD_SECTIONS),
        ])
        buckets = {}
        for line in lines:
            info = Extractor._tax_amounts_for_line(line.move_id, line)
            sign = -1 if line.move_id.move_type in ('out_refund', 'in_refund') else 1
            bucket = buckets.setdefault(info['gst_rate'], {
                'rate': info['gst_rate'], 'taxable_value': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0,
            })
            bucket['taxable_value'] += sign * info['taxable_value']
            for head in HEADS:
                bucket[head] += sign * info['%s_amount' % head]
        return sorted(buckets.values(), key=lambda b: b['rate'])

    def _armora_expense_lines(self):
        """Table 14: ITC on bills, spread over each bill's expense lines by value."""
        self.ensure_one()
        itc_by_move = self._armora_input_tax_by_move()
        if not itc_by_move:
            return []
        moves = self.env['account.move'].browse(list(itc_by_move))
        by_account = {}
        for move in moves:
            product_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            total = sum(product_lines.mapped(lambda l: abs(l.balance))) or 1.0
            for line in product_lines:
                bucket = by_account.setdefault(line.account_id, {
                    'account_id': line.account_id.id,
                    'name': line.account_id.display_name,
                    'expense_value': 0.0,
                    'itc_amount': 0.0,
                })
                bucket['expense_value'] += line.balance
                bucket['itc_amount'] += itc_by_move[move.id] * abs(line.balance) / total
        currency = self.currency_id
        return [
            dict(vals, expense_value=currency.round(vals['expense_value']), itc_amount=currency.round(vals['itc_amount']))
            for vals in sorted(by_account.values(), key=lambda v: -v['itc_amount'])
        ]
