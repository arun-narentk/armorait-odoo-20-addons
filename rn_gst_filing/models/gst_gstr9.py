# -*- coding: utf-8 -*-
from ast import literal_eval
from collections import defaultdict
from datetime import date

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from .gstr9_rows import ROWS, ROW_INFO, TOTAL_ORDER, TOTALS

HEADS = ('igst', 'cgst', 'sgst', 'cess')
KIND_FIELDS = {
    'tax': ('value',) + HEADS,
    'value': ('value',),
    'itc': HEADS,
    'pay': ('value', 'cash') + HEADS,
}
SALE_TYPES = ('out_invoice', 'out_refund', 'out_receipt')
PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')

# GSTR section of a sale line -> GSTR-9 row, by document kind (invoice, credit note, debit note).
SALE_ROWS = {
    'sale_b2cl': ('4A', '4A', '4A'),
    'sale_b2cs': ('4A', '4A', '4A'),
    'sale_b2b_regular': ('4B', '4I', '4J'),
    'sale_exp_wp': ('4C', '4I', '4J'),
    'sale_sez_wp': ('4D', '4I', '4J'),
    'sale_deemed_export': ('4E', '4I', '4J'),
    'sale_cdnr_regular': ('4J', '4I', '4J'),
    'sale_cdnr_deemed_export': ('4J', '4I', '4J'),
    'sale_cdnr_sez_wp': ('4J', '4I', '4J'),
    'sale_cdnur_b2cl': ('4J', '4I', '4J'),
    'sale_cdnur_exp_wp': ('4J', '4I', '4J'),
    'sale_exp_wop': ('5A', '5H', '5I'),
    'sale_sez_wop': ('5B', '5H', '5I'),
    'sale_b2b_rcm': ('5C', '5H', '5I'),
    'sale_exempt': ('5D', '5H', '5I'),
    'sale_nil_rated': ('5E', '5H', '5I'),
    'sale_non_gst_supplies': ('5F', '5H', '5I'),
    'sale_cdnr_sez_wop': ('5I', '5H', '5I'),
    'sale_cdnur_exp_wop': ('5I', '5H', '5I'),
    'sale_cdnr_rcm': ('5I', '5H', '5I'),
}
# Rows where a document of that kind is reported as a positive amount that the
# return then subtracts (credit notes), instead of being netted into the row.
SUBTRACTED_ROWS = ('4I', '5H')
RCM_INWARD_SECTIONS = (
    'purchase_b2b_rcm', 'purchase_b2c_rcm', 'purchase_imp_services', 'purchase_cdnr_rcm', 'purchase_cdnur_rcm',
)
REGULAR_ITC_SECTIONS = ('purchase_b2b_regular', 'purchase_cdnr_regular')
CAPITAL_ACCOUNT_TYPES = ('asset_fixed', 'asset_non_current')


class RnGstGstr9(models.Model):
    _name = 'rn.gst.gstr9'
    _description = 'GSTR-9 Annual Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'financial_year desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    gstin = fields.Char(required=True, tracking=True, index=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    date_from = fields.Date(compute='_compute_dates', store=True)
    date_to = fields.Date(compute='_compute_dates', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Filled'),
        ('filed', 'Filed'),
    ], default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', string='Rows')
    part2_line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', domain=[('part', '=', '2')])
    part3_line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', domain=[('part', '=', '3')])
    part4_line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', domain=[('part', '=', '4')])
    part5_line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', domain=[('part', '=', '5')])
    part6_line_ids = fields.One2many('rn.gst.gstr9.line', 'gstr9_id', domain=[('part', '=', '6')])
    hsn_ids = fields.One2many('rn.gst.gstr9.hsn', 'gstr9_id', string='HSN Summary')
    hsn_outward_ids = fields.One2many('rn.gst.gstr9.hsn', 'gstr9_id', domain=[('direction', '=', 'outward')])
    hsn_inward_ids = fields.One2many('rn.gst.gstr9.hsn', 'gstr9_id', domain=[('direction', '=', 'inward')])
    gstr3b_months = fields.Integer(string='GSTR-3B Months Found', readonly=True, copy=False)
    filled_at = fields.Datetime(string='Filled from Books On', readonly=True, copy=False)
    fill_warning = fields.Text(string='Warnings', readonly=True, copy=False)
    notes = fields.Text()

    _rn_gst_gstr9_uniq = models.Constraint(
        'unique(company_id, gstin, financial_year)',
        "A GSTR-9 already exists for this company, GSTIN and financial year.",
    )

    @api.depends('financial_year')
    def _compute_dates(self):
        Period = self.env['rn.gst.filing.period']
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
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.gstr9') or _('New')
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
            'state', 'notes', 'message_follower_ids', 'activity_ids', 'message_ids',
        } and not self.env.su:
            raise UserError(_('A filed GSTR-9 is read-only. Reset it to draft first.'))
        return super().write(vals)

    def action_mark_filed(self):
        self.write({'state': 'filed'})
        for rec in self:
            rec.message_post(body=_('GSTR-9 marked as filed.'))
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True

    # ------------------------------------------------------------------
    # Fill from books
    # ------------------------------------------------------------------

    def action_fill_from_books(self):
        """Fill Tables 4 to 9, 16A, 17 and 18 from the year's posted documents,
        GSTR-3B records and GSTR-2B reconciliations. Manual rows are kept."""
        for rec in self:
            if rec.state == 'filed':
                raise UserError(_('A filed GSTR-9 is read-only. Reset it to draft first.'))
            rec._rn_sync_rows()
            amounts = defaultdict(lambda: defaultdict(float))
            warnings = []
            rec._rn_books_outward(amounts, warnings)
            rec._rn_books_inward(amounts)
            months = rec._rn_from_gstr3b(amounts, warnings)
            rec._rn_from_gstr2b(amounts, warnings)
            currency = rec.currency_id
            for line in rec.line_ids.filtered(lambda l: l.source in ('books', 'gstr3b', 'gstr2b')):
                row = amounts.get(line.code, {})
                line.with_context(rn_gstr9_totals=True).write({
                    name: currency.round(row.get(name, 0.0)) for name in KIND_FIELDS[line.kind]
                })
            rec.hsn_ids.unlink()
            rec.write({
                'hsn_ids': [Command.create(vals) for vals in rec._rn_hsn_lines()],
                'gstr3b_months': months,
                'filled_at': fields.Datetime.now(),
                'fill_warning': '\n'.join(warnings) or False,
                'state': 'computed',
            })
            rec._rn_recompute_totals()
            rec.message_post(body=_(
                'GSTR-9 filled from books for %(fy)s. Total turnover %(turnover)s. GSTR-3B months found: %(months)s of 12.',
                fy=rec.financial_year, turnover=rec._rn_row('5N').value, months=months,
            ))
        return True

    def _rn_sync_rows(self):
        """Bring the rows of an older return in line with the current row list."""
        self.ensure_one()
        existing = {line.code: line for line in self.line_ids}
        missing = []
        for index, (code, part, table, label, kind, source) in enumerate(ROWS):
            line = existing.get(code)
            vals = {'sequence': index, 'part': part, 'table': table, 'label': label, 'kind': kind, 'source': source}
            if not line:
                missing.append(Command.create(dict(vals, code=code)))
            elif any(line[name] != value for name, value in vals.items()):
                line.with_context(rn_gstr9_totals=True).write(vals)
        if missing:
            self.write({'line_ids': missing})

    def _rn_row(self, code):
        self.ensure_one()
        return self.line_ids.filtered(lambda l: l.code == code)[:1]

    def _rn_recompute_totals(self):
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
                values[code] = total
                line.with_context(rn_gstr9_totals=True).write(total)

    def _rn_line_domain(self, move_types):
        self.ensure_one()
        return [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_id.move_type', 'in', move_types),
        ]

    @api.model
    def _rn_document_kind(self, move):
        if move.move_type == 'out_refund':
            return 1
        if move.debit_origin_id:
            return 2
        return 0

    def _rn_books_outward(self, amounts, warnings):
        Line = self.env['account.move.line']
        groups = Line._read_group(
            self._rn_line_domain(SALE_TYPES) + [
                ('display_type', 'in', ('product', 'tax')),
                ('l10n_in_gstr_section', '!=', False),
            ],
            ['move_id', 'l10n_in_gstr_section', 'display_type', 'tax_line_id'],
            ['balance:sum'],
        )
        eco_lines = 0
        for move, section, display_type, tax, balance in groups:
            if section == 'sale_eco_9_5':
                eco_lines += 1
                continue
            rows = SALE_ROWS.get(section)
            if not rows:
                continue
            code = rows[self._rn_document_kind(move)]
            # Sales are credits; a credit note row shows the note as a positive amount.
            amount = balance if code in SUBTRACTED_ROWS else -balance
            if display_type == 'product':
                amounts[code]['value'] += amount
            elif tax.l10n_in_gst_tax_type and ROW_INFO[code][4] == 'tax':
                amounts[code][tax.l10n_in_gst_tax_type] += amount
        if eco_lines:
            warnings.append(_('Supplies through e-commerce operators (section 9(5)) are not filled; enter them by hand.'))

    def _rn_books_inward(self, amounts):
        Line = self.env['account.move.line']
        domain = self._rn_line_domain(PURCHASE_TYPES)
        for section, display_type, tax, balance in Line._read_group(
            domain + [('display_type', 'in', ('product', 'tax')), ('l10n_in_gstr_section', '!=', False)],
            ['l10n_in_gstr_section', 'display_type', 'tax_line_id'],
            ['balance:sum'],
        ):
            head = tax.l10n_in_gst_tax_type
            if section in RCM_INWARD_SECTIONS:
                if display_type == 'product':
                    amounts['4G']['value'] += balance
                elif head:
                    # The tagged -100% line of a reverse charge tax is the tax owed.
                    amounts['4G'][head] -= balance
            elif section == 'purchase_imp_goods' and display_type == 'tax' and head:
                amounts['6E'][head] += balance
                amounts['8G'][head] += balance
            elif section == 'purchase_composition_supplies' and display_type == 'product':
                amounts['16A']['value'] += balance

        # ITC on reverse charge: the +100% line of the tax, which carries no GST tag.
        for move, tax, balance in Line._read_group(
            domain + [
                ('display_type', '=', 'tax'),
                ('tax_line_id.l10n_in_reverse_charge', '=', True),
                ('tax_repartition_line_id.factor_percent', '>', 0),
            ],
            ['move_id', 'tax_line_id'], ['balance:sum'],
        ):
            head = tax.l10n_in_gst_tax_type
            if not head:
                continue
            treatment = move.l10n_in_gst_treatment
            code = '6F' if treatment == 'overseas' else '6C' if treatment in ('unregistered', 'consumer') else '6D'
            amounts[code][head] += balance

        # Regular ITC split into inputs, capital goods and input services, in
        # proportion to the bill lines of each kind.
        itc_by_move = defaultdict(lambda: defaultdict(float))
        for move, tax, balance in Line._read_group(
            domain + [('display_type', '=', 'tax'), ('l10n_in_gstr_section', 'in', REGULAR_ITC_SECTIONS)],
            ['move_id', 'tax_line_id'], ['balance:sum'],
        ):
            if tax.l10n_in_gst_tax_type:
                itc_by_move[move][tax.l10n_in_gst_tax_type] += balance
        if not itc_by_move:
            return
        moves = self.env['account.move'].browse([move.id for move in itc_by_move])
        base_by_move = defaultdict(lambda: defaultdict(float))
        for line in moves.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            if line.account_id.account_type in CAPITAL_ACCOUNT_TYPES:
                kind = '6B2'
            elif line.product_id.type == 'service':
                kind = '6B3'
            else:
                kind = '6B1'
            base_by_move[line.move_id][kind] += abs(line.balance)
        for move, heads in itc_by_move.items():
            bases = base_by_move.get(move) or {'6B1': 1.0}
            total_base = sum(bases.values()) or 1.0
            for kind, base in bases.items():
                for head, tax_amount in heads.items():
                    amounts[kind][head] += tax_amount * base / total_base

    def _rn_from_gstr3b(self, amounts, warnings):
        if 'rn.gst.3b' not in self.env:
            warnings.append(_('Armora GST GSTR-3B is not installed: Tables 6A, 6G, 6H, 7E, 7H and 9 were not filled.'))
            return 0
        # Only totals of this return's company are read; users preparing GSTR-9
        # may hold no rights on the GSTR-3B app itself.
        Gstr3b = self.env['rn.gst.3b'].sudo()
        records = Gstr3b.search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('financial_year', '=', self.financial_year),
            ('state', 'in', ('computed', 'filed')),
        ])
        has_tables = 't4a5_igst' in Gstr3b._fields
        for rec in records:
            for head in HEADS:
                if has_tables:
                    available = sum(
                        rec['t4a%s_%s' % (row, head)] for row in '12345' if 't4a%s_%s' % (row, head) in rec._fields
                    )
                    if not available:
                        # Filled by hand: the 6.1 ITC is the net credit, add back the reversals.
                        available = rec['itc_available_%s' % head] + rec['t4b1_%s' % head] + rec['t4b2_%s' % head]
                    amounts['6A'][head] += available
                    amounts['6G'][head] += rec['t4a4_%s' % head]
                    amounts['6H'][head] += rec['t4d1_%s' % head]
                    amounts['7E'][head] += rec['t4b1_%s' % head]
                    amounts['7H'][head] += rec['t4b2_%s' % head]
                    rcm = rec['t31d_%s' % head]
                else:
                    amounts['6A'][head] += rec['itc_available_%s' % head]
                    rcm = 0.0
                code = '9%s' % head.upper()
                amounts[code]['value'] += rec['liability_%s' % head] + rcm
                amounts[code]['cash'] += rec['cash_payable_%s' % head]
            for step in self._rn_utilization_steps(rec):
                code = '9%s' % step['to'].upper()
                if code in ROW_INFO and step['from'] in HEADS:
                    amounts[code][step['from']] += step['amount']
            amounts['9INT']['value'] += rec.self_assessed_interest
            amounts['9INT']['cash'] += rec.self_assessed_interest
        months = len(set(records.mapped('return_period')))
        if months < 12:
            warnings.append(_(
                'Only %s of 12 GSTR-3B months are filled for this year: Tables 6A, 7 and 9 cover those months only.',
                months,
            ))
        return months

    @api.model
    def _rn_utilization_steps(self, gstr3b):
        try:
            steps = literal_eval(gstr3b.itc_utilization_audit or '[]')
        except (ValueError, SyntaxError):
            return []
        return [s for s in steps if isinstance(s, dict) and {'from', 'to', 'amount'} <= set(s)]

    def _rn_from_gstr2b(self, amounts, warnings):
        if 'rn.gst.gstr2b.line' not in self.env:
            warnings.append(_('Armora GST 2A/2B Reconciliation is not installed: Table 8A was not filled.'))
            return
        # Only totals of this return's company are read; users preparing GSTR-9
        # may hold no rights on the GSTR-2B app itself.
        Line2b = self.env['rn.gst.gstr2b.line'].sudo()
        domain = [
            ('reconciliation_id.company_id', '=', self.company_id.id),
            ('reconciliation_id.financial_year', '=', self.financial_year),
            ('reconciliation_id.state', '!=', 'cancelled'),
            ('source', '=', 'gstr2b'),
            ('itc_availability', '!=', 'n'),
        ]
        domain.append(('reconciliation_id.gstin', '=', self.gstin))
        if 'statement_type' in self.env['rn.gst.gstr2b']._fields:
            domain.append(('reconciliation_id.statement_type', '=', 'gstr2b'))
        lines = Line2b.search(domain)
        if not lines:
            warnings.append(_('No GSTR-2B reconciliation found for this year: Table 8A is zero.'))
        for line in lines:
            sign = -1 if line.document_type == 'credit_note' else 1
            for head in HEADS:
                amounts['8A'][head] += sign * line['%s_amount' % head]

    def _rn_hsn_lines(self):
        """Tables 17 and 18: HSN-wise summary of outward and inward supplies."""
        self.ensure_one()
        Extractor = self.env['rn.gst.data.extractor']
        Line = self.env['account.move.line']
        result = []
        for direction, move_types in (('outward', SALE_TYPES), ('inward', PURCHASE_TYPES)):
            lines = Line.search(self._rn_line_domain(move_types) + [
                ('display_type', '=', 'product'),
                ('l10n_in_hsn_code', '!=', False),
                ('l10n_in_gstr_section', 'not in', (False, 'sale_out_of_scope', 'purchase_out_of_scope')),
            ])
            buckets = {}
            for line in lines:
                info = Extractor._tax_amounts_for_line(line.move_id, line)
                sign = -1 if line.move_id.move_type in ('out_refund', 'in_refund') else 1
                uqc = line.product_uom_id.l10n_in_code or line.product_uom_id.name or ''
                key = (line.l10n_in_hsn_code, uqc, info['gst_rate'])
                bucket = buckets.setdefault(key, {
                    'direction': direction, 'hsn_code': key[0], 'uqc': uqc, 'rate': key[2],
                    'quantity': 0.0, 'taxable_value': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0,
                })
                bucket['quantity'] += sign * line.quantity
                bucket['taxable_value'] += sign * info['taxable_value']
                for head in HEADS:
                    bucket[head] += sign * info['%s_amount' % head]
            result += sorted(buckets.values(), key=lambda b: (b['hsn_code'], b['rate']))
        return result
