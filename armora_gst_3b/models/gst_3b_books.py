# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

HEADS = ('igst', 'cgst', 'sgst', 'cess')

# GSTR section that Odoo's Indian localization sets on every posted product
# and tax line, mapped to the GSTR-3B Table 3.1 row it belongs to.
OUTWARD_ROWS = {
    'sale_b2b_regular': 't31a',
    'sale_b2cl': 't31a',
    'sale_b2cs': 't31a',
    'sale_deemed_export': 't31a',
    'sale_cdnr_regular': 't31a',
    'sale_cdnr_deemed_export': 't31a',
    'sale_cdnur_b2cl': 't31a',
    'sale_exp_wp': 't31b',
    'sale_exp_wop': 't31b',
    'sale_sez_wp': 't31b',
    'sale_sez_wop': 't31b',
    'sale_cdnr_sez_wp': 't31b',
    'sale_cdnr_sez_wop': 't31b',
    'sale_cdnur_exp_wp': 't31b',
    'sale_cdnur_exp_wop': 't31b',
    'sale_nil_rated': 't31c',
    'sale_exempt': 't31c',
    'sale_non_gst_supplies': 't31e',
}
# Outward supplies taxed under reverse charge (sale_b2b_rcm, sale_cdnr_rcm) are
# reported by the buyer only and go in no row of Table 3.1.
RCM_INWARD_SECTIONS = (
    'purchase_b2b_rcm', 'purchase_b2c_rcm', 'purchase_imp_services', 'purchase_cdnr_rcm', 'purchase_cdnur_rcm',
)
REGULAR_ITC_SECTIONS = ('purchase_b2b_regular', 'purchase_cdnr_regular')
EXEMPT_INWARD_SECTIONS = ('purchase_nil_rated', 'purchase_exempt', 'purchase_composition_supplies')
INTERSTATE_SECTIONS = ('sale_b2cl', 'sale_b2cs', 'sale_cdnur_b2cl', 'sale_b2b_regular', 'sale_cdnr_regular')
INTERSTATE_TYPES = {
    'unregistered': 'unregistered',
    'consumer': 'unregistered',
    'composition': 'composition',
    'uin_holders': 'uin',
}
PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')

# Rows recomputed by "Fill from Books". 4(A)(4) ISD, 4(B)(2) and 4(D)(1) are
# entered by hand and kept on refill.
BOOK_FIELDS = (
    ['t31a_taxable'] + ['t31a_%s' % h for h in HEADS]
    + ['t31b_taxable', 't31b_igst', 't31b_cess', 't31c_taxable', 't31e_taxable']
    + ['t31d_taxable'] + ['t31d_%s' % h for h in HEADS]
    + ['t4a1_igst', 't4a1_cess', 't4a2_igst', 't4a2_cess']
    + ['t4a3_%s' % h for h in HEADS] + ['t4a5_%s' % h for h in HEADS]
    + ['t4b1_%s' % h for h in HEADS] + ['t4d2_%s' % h for h in HEADS]
    + ['t5_exempt_inter', 't5_exempt_intra', 't5_nongst_inter', 't5_nongst_intra']
)

ITC_AVAILABLE_FIELDS = (
    ['t4a1_igst', 't4a1_cess', 't4a2_igst', 't4a2_cess']
    + ['t4a%s_%s' % (row, h) for row in '345' for h in HEADS]
)
ITC_REVERSED_FIELDS = ['t4b%s_%s' % (row, h) for row in '12' for h in HEADS]


class ArmoraGst3b(models.Model):
    _inherit = 'armora.gst.3b'

    # Table 3.1
    t31a_taxable = fields.Monetary(string='3.1(a) Taxable Value', currency_field='currency_id')
    t31a_igst = fields.Monetary(string='3.1(a) IGST', currency_field='currency_id')
    t31a_cgst = fields.Monetary(string='3.1(a) CGST', currency_field='currency_id')
    t31a_sgst = fields.Monetary(string='3.1(a) SGST', currency_field='currency_id')
    t31a_cess = fields.Monetary(string='3.1(a) Cess', currency_field='currency_id')
    t31b_taxable = fields.Monetary(string='3.1(b) Taxable Value', currency_field='currency_id')
    t31b_igst = fields.Monetary(string='3.1(b) IGST', currency_field='currency_id')
    t31b_cess = fields.Monetary(string='3.1(b) Cess', currency_field='currency_id')
    t31c_taxable = fields.Monetary(string='3.1(c) Taxable Value', currency_field='currency_id')
    t31d_taxable = fields.Monetary(string='3.1(d) Taxable Value', currency_field='currency_id')
    t31d_igst = fields.Monetary(string='3.1(d) IGST', currency_field='currency_id')
    t31d_cgst = fields.Monetary(string='3.1(d) CGST', currency_field='currency_id')
    t31d_sgst = fields.Monetary(string='3.1(d) SGST', currency_field='currency_id')
    t31d_cess = fields.Monetary(string='3.1(d) Cess', currency_field='currency_id')
    t31e_taxable = fields.Monetary(string='3.1(e) Taxable Value', currency_field='currency_id')

    # Table 3.2
    interstate_line_ids = fields.One2many(
        'armora.gst.3b.interstate.line', 'filing_id', string='3.2 Inter-State Supplies',
    )

    # Table 4(A) ITC available
    t4a1_igst = fields.Monetary(string='4(A)(1) IGST', currency_field='currency_id')
    t4a1_cess = fields.Monetary(string='4(A)(1) Cess', currency_field='currency_id')
    t4a2_igst = fields.Monetary(string='4(A)(2) IGST', currency_field='currency_id')
    t4a2_cess = fields.Monetary(string='4(A)(2) Cess', currency_field='currency_id')
    t4a3_igst = fields.Monetary(string='4(A)(3) IGST', currency_field='currency_id')
    t4a3_cgst = fields.Monetary(string='4(A)(3) CGST', currency_field='currency_id')
    t4a3_sgst = fields.Monetary(string='4(A)(3) SGST', currency_field='currency_id')
    t4a3_cess = fields.Monetary(string='4(A)(3) Cess', currency_field='currency_id')
    t4a4_igst = fields.Monetary(string='4(A)(4) IGST', currency_field='currency_id')
    t4a4_cgst = fields.Monetary(string='4(A)(4) CGST', currency_field='currency_id')
    t4a4_sgst = fields.Monetary(string='4(A)(4) SGST', currency_field='currency_id')
    t4a4_cess = fields.Monetary(string='4(A)(4) Cess', currency_field='currency_id')
    t4a5_igst = fields.Monetary(string='4(A)(5) IGST', currency_field='currency_id')
    t4a5_cgst = fields.Monetary(string='4(A)(5) CGST', currency_field='currency_id')
    t4a5_sgst = fields.Monetary(string='4(A)(5) SGST', currency_field='currency_id')
    t4a5_cess = fields.Monetary(string='4(A)(5) Cess', currency_field='currency_id')

    # Table 4(B) ITC reversed
    t4b1_igst = fields.Monetary(string='4(B)(1) IGST', currency_field='currency_id')
    t4b1_cgst = fields.Monetary(string='4(B)(1) CGST', currency_field='currency_id')
    t4b1_sgst = fields.Monetary(string='4(B)(1) SGST', currency_field='currency_id')
    t4b1_cess = fields.Monetary(string='4(B)(1) Cess', currency_field='currency_id')
    t4b2_igst = fields.Monetary(string='4(B)(2) IGST', currency_field='currency_id')
    t4b2_cgst = fields.Monetary(string='4(B)(2) CGST', currency_field='currency_id')
    t4b2_sgst = fields.Monetary(string='4(B)(2) SGST', currency_field='currency_id')
    t4b2_cess = fields.Monetary(string='4(B)(2) Cess', currency_field='currency_id')

    # Table 4(C) net ITC = 4(A) - 4(B)
    t4c_igst = fields.Monetary(string='4(C) IGST', currency_field='currency_id', compute='_compute_t4c')
    t4c_cgst = fields.Monetary(string='4(C) CGST', currency_field='currency_id', compute='_compute_t4c')
    t4c_sgst = fields.Monetary(string='4(C) SGST', currency_field='currency_id', compute='_compute_t4c')
    t4c_cess = fields.Monetary(string='4(C) Cess', currency_field='currency_id', compute='_compute_t4c')

    # Table 4(D) other details
    t4d1_igst = fields.Monetary(string='4(D)(1) IGST', currency_field='currency_id')
    t4d1_cgst = fields.Monetary(string='4(D)(1) CGST', currency_field='currency_id')
    t4d1_sgst = fields.Monetary(string='4(D)(1) SGST', currency_field='currency_id')
    t4d1_cess = fields.Monetary(string='4(D)(1) Cess', currency_field='currency_id')
    t4d2_igst = fields.Monetary(string='4(D)(2) IGST', currency_field='currency_id')
    t4d2_cgst = fields.Monetary(string='4(D)(2) CGST', currency_field='currency_id')
    t4d2_sgst = fields.Monetary(string='4(D)(2) SGST', currency_field='currency_id')
    t4d2_cess = fields.Monetary(string='4(D)(2) Cess', currency_field='currency_id')

    # Table 5 exempt, nil rated and non-GST inward supplies
    t5_exempt_inter = fields.Monetary(string='5 Composition/Exempt/Nil Inter-State', currency_field='currency_id')
    t5_exempt_intra = fields.Monetary(string='5 Composition/Exempt/Nil Intra-State', currency_field='currency_id')
    t5_nongst_inter = fields.Monetary(string='5 Non-GST Inter-State', currency_field='currency_id')
    t5_nongst_intra = fields.Monetary(string='5 Non-GST Intra-State', currency_field='currency_id')

    books_filled_at = fields.Datetime(string='Filled from Books On', readonly=True, copy=False)
    books_warning = fields.Text(string='Books Warnings', readonly=True, copy=False)

    @api.depends(*ITC_AVAILABLE_FIELDS, *ITC_REVERSED_FIELDS)
    def _compute_t4c(self):
        for rec in self:
            for head in HEADS:
                available = sum(rec[name] for name in ITC_AVAILABLE_FIELDS if name.endswith('_' + head))
                reversed_itc = sum(rec[name] for name in ITC_REVERSED_FIELDS if name.endswith('_' + head))
                rec['t4c_%s' % head] = available - reversed_itc

    def action_fill_from_books(self):
        """Fill Tables 3.1, 3.2, 4 and 5 from posted invoices and bills, then
        carry the liability and net ITC into Table 6.1 and set off ITC."""
        for rec in self:
            if rec.state == 'filed':
                raise UserError(_('Filed GSTR-3B records are read-only.'))
            vals, interstate, warnings = rec._armora_books_values()
            rec._armora_itc_ledger_values(vals, warnings)
            rec._armora_rcm_time_of_supply_warnings(warnings)
            vals.update({
                'interstate_line_ids': [Command.clear()] + [Command.create(line) for line in interstate],
                'books_filled_at': fields.Datetime.now(),
                'books_warning': '\n'.join(warnings) or False,
            })
            rec.write(vals)
            rec.write({
                **{'liability_%s' % h: rec['t31a_%s' % h] + (rec['t31b_%s' % h] if 't31b_%s' % h in rec._fields else 0.0)
                   for h in HEADS},
                **{'itc_available_%s' % h: rec['t4c_%s' % h] for h in HEADS},
            })
        self.action_compute_itc_utilization()
        for rec in self:
            # Interest under Rule 88B runs on the part of the liability paid in cash.
            rec.net_tax_liability = sum(rec['cash_payable_%s' % h] for h in HEADS)
            rec.message_post(body=_(
                'Tables 3.1, 3.2, 4 and 5 filled from posted invoices and bills. '
                'Output tax %(output)s, net ITC %(itc)s, cash payable %(cash)s.',
                output=sum(rec['liability_%s' % h] + rec['t31d_%s' % h] for h in HEADS),
                itc=sum(rec['t4c_%s' % h] for h in HEADS),
                cash=rec.net_tax_liability,
            ))
        return True

    def _armora_itc_ledger_values(self, vals, warnings):
        """Take reversals, reclaims and the opening credit from the month's ITC ledger
        (Armora GST ITC), when that app is installed."""
        self.ensure_one()
        if 'armora.gst.itc.ledger' not in self.env:
            return
        Ledger = self.env['armora.gst.itc.ledger'].sudo()
        company_domain = [('company_id', '=', self.company_id.id), ('gstin', '=', self.gstin)]
        ledger = Ledger.search(company_domain + [
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
            ('state', 'in', ('computed', 'locked')),
        ], limit=1)
        if not ledger:
            if Ledger.search_count(company_domain, limit=1):
                warnings.append(_('No computed ITC ledger for this month: Rule 37, Rule 42 and blocked credit are not reversed.'))
            return
        for head in HEADS:
            vals['t4b1_%s' % head] += ledger['blocked_%s' % head] + ledger['rule42_%s' % head]
            vals['t4b2_%s' % head] = ledger['rule37_%s' % head]
            # Reclaimed credit is claimed again in 4(A)(5) and also shown in 4(D)(1).
            vals['t4a5_%s' % head] += ledger['reclaimed_%s' % head]
            vals['t4d1_%s' % head] = ledger['reclaimed_%s' % head]
            vals['itc_opening_%s' % head] = ledger['opening_%s' % head]

    def _armora_rcm_time_of_supply_warnings(self, warnings):
        """Point out reverse charge bills whose tax falls due in another month than their
        invoice date (Armora GST Reverse Charge computes the time of supply)."""
        self.ensure_one()
        Move = self.env['account.move']
        if 'armora_rcm_tos_date' not in Move._fields:
            return
        bills = Move.search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', PURCHASE_TYPES),
            ('state', '=', 'posted'),
            ('armora_is_rcm', '=', True),
            ('invoice_date', '>=', self.period_start - timedelta(days=62)),
            ('invoice_date', '<=', self.period_end),
        ])

        def in_period(day):
            return day and self.period_start <= day <= self.period_end

        later = bills.filtered(lambda b: in_period(b.invoice_date) and not in_period(b.armora_rcm_tos_date))
        earlier = bills.filtered(lambda b: not in_period(b.invoice_date) and in_period(b.armora_rcm_tos_date))
        if later:
            warnings.append(_(
                'Reverse charge on %(count)s bills of this month falls due in a later month by time of supply: %(names)s',
                count=len(later), names=', '.join(later[:5].mapped('name')),
            ))
        if earlier:
            warnings.append(_(
                'Reverse charge on %(count)s bills of earlier months falls due in this month by time of supply: %(names)s',
                count=len(earlier), names=', '.join(earlier[:5].mapped('name')),
            ))

    def action_compute_itc_utilization(self):
        res = super().action_compute_itc_utilization()
        # Reverse charge tax (Table 3.1(d)) can only be paid in cash, never from ITC.
        for rec in self:
            if any(rec['t31d_%s' % h] for h in HEADS):
                rec.write({'cash_payable_%s' % h: rec['cash_payable_%s' % h] + rec['t31d_%s' % h] for h in HEADS})
        return res

    def _armora_books_values(self):
        self.ensure_one()
        Line = self.env['account.move.line']
        currency = self.currency_id
        base = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('invoice_date', '>=', self.period_start),
            ('invoice_date', '<=', self.period_end),
        ]
        vals = defaultdict(float)
        warnings = []

        def add(field_name, amount):
            if field_name in self._fields:
                vals[field_name] += amount

        # Base values of product lines. Sales are credits, so the sign is flipped.
        for section, balance in Line._read_group(
            base + [('display_type', '=', 'product'), ('l10n_in_gstr_section', '!=', False)],
            ['l10n_in_gstr_section'], ['balance:sum'],
        ):
            row = OUTWARD_ROWS.get(section)
            if row:
                add('%s_taxable' % row, -balance)
            elif section in RCM_INWARD_SECTIONS:
                add('t31d_taxable', balance)
            elif section == 'sale_eco_9_5':
                warnings.append(_('Supplies through e-commerce operators (section 9(5)) are not filled: enter Table 3.1.1 on the portal.'))

        # Tax lines. Their GST tags decide the section, so the offsetting line of an
        # export under LUT or of a reverse charge tax is out of scope and skipped.
        for section, tax, balance in Line._read_group(
            base + [('display_type', '=', 'tax'), ('l10n_in_gstr_section', '!=', False)],
            ['l10n_in_gstr_section', 'tax_line_id'], ['balance:sum'],
        ):
            head = tax.l10n_in_gst_tax_type
            if not head:
                continue
            row = OUTWARD_ROWS.get(section)
            if row in ('t31a', 't31b'):
                add('%s_%s' % (row, head), -balance)
            elif section in RCM_INWARD_SECTIONS:
                add('t31d_%s' % head, -balance)
            elif section == 'purchase_imp_goods':
                add('t4a1_%s' % head, balance)
            elif section in REGULAR_ITC_SECTIONS:
                add('t4a5_%s' % head, balance)

        # ITC on reverse charge: the +100% line of the tax, which carries no GST tag.
        for move, tax, balance in Line._read_group(
            base + [
                ('display_type', '=', 'tax'),
                ('move_id.move_type', 'in', PURCHASE_TYPES),
                ('tax_line_id.l10n_in_reverse_charge', '=', True),
                ('tax_repartition_line_id.factor_percent', '>', 0),
            ],
            ['move_id', 'tax_line_id'], ['balance:sum'],
        ):
            head = tax.l10n_in_gst_tax_type
            if head:
                row = 't4a2' if move.l10n_in_gst_treatment == 'overseas' else 't4a3'
                add('%s_%s' % (row, head), balance)

        # Blocked credit (NON ITC tag) stays in 4(A) and is reversed in 4(B)(1), as
        # Circular 170/02/2022 requires. "Other NON ITC" goes to 4(D)(2) only.
        for xmlid, row in (('l10n_in.tax_tag_non_itc', 't4b1'), ('l10n_in.tax_tag_other_non_itc', 't4d2')):
            tag = self.env.ref(xmlid, raise_if_not_found=False)
            if not tag:
                continue
            for section, tax, balance in Line._read_group(
                base + [
                    ('display_type', '=', 'tax'),
                    ('move_id.move_type', 'in', PURCHASE_TYPES),
                    ('tax_tag_ids', 'in', tag.ids),
                ],
                ['l10n_in_gstr_section', 'tax_line_id'], ['balance:sum'],
            ):
                head = tax.l10n_in_gst_tax_type
                if not head:
                    continue
                add('%s_%s' % (row, head), balance)
                in_regular_itc = section in REGULAR_ITC_SECTIONS
                if row == 't4b1' and not in_regular_itc:
                    add('t4a5_%s' % head, balance)
                elif row == 't4d2' and in_regular_itc:
                    add('t4a5_%s' % head, -balance)

        # Table 5: inter-state when the place of supply differs from the supplier state.
        for move, section, balance in Line._read_group(
            base + [
                ('display_type', '=', 'product'),
                ('l10n_in_gstr_section', 'in', EXEMPT_INWARD_SECTIONS + ('purchase_non_gst_supplies',)),
            ],
            ['move_id', 'l10n_in_gstr_section'], ['balance:sum'],
        ):
            kind = 'nongst' if section == 'purchase_non_gst_supplies' else 'exempt'
            intra = move.l10n_in_state_id == move.commercial_partner_id.state_id
            add('t5_%s_%s' % (kind, 'intra' if intra else 'inter'), balance)

        # Table 3.2: inter-state supplies to unregistered, composition and UIN holders.
        company_state = self.company_id.state_id
        interstate = defaultdict(lambda: {'taxable_value': 0.0, 'igst': 0.0})
        for move, display_type, tax, balance in Line._read_group(
            base + [
                ('display_type', 'in', ('product', 'tax')),
                ('l10n_in_gstr_section', 'in', INTERSTATE_SECTIONS),
            ],
            ['move_id', 'display_type', 'tax_line_id'], ['balance:sum'],
        ):
            supply_type = INTERSTATE_TYPES.get(move.l10n_in_gst_treatment)
            state = move.l10n_in_state_id
            if not supply_type or not state or state == company_state:
                continue
            bucket = interstate[supply_type, state.id]
            if display_type == 'product':
                bucket['taxable_value'] -= balance
            elif tax.l10n_in_gst_tax_type == 'igst':
                bucket['igst'] -= balance

        out_of_scope = Line.search_count(base + [
            ('display_type', '=', 'product'),
            ('l10n_in_gstr_section', 'in', ('sale_out_of_scope', 'purchase_out_of_scope')),
            ('balance', '!=', 0),
        ])
        if out_of_scope:
            warnings.append(_(
                '%s invoice or bill lines are out of GST scope (no GST tax) and were left out.', out_of_scope,
            ))
        no_section = Line.search_count(base + [
            ('display_type', '=', 'product'),
            ('l10n_in_gstr_section', '=', False),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
            ('balance', '!=', 0),
        ])
        if no_section:
            warnings.append(_(
                '%s invoice or bill lines have no GSTR section (posted before Indian localization) and were left out.',
                no_section,
            ))

        values = {name: currency.round(vals.get(name, 0.0)) for name in BOOK_FIELDS}
        lines = [
            {
                'supply_type': supply_type,
                'state_id': state_id,
                'taxable_value': currency.round(amounts['taxable_value']),
                'igst': currency.round(amounts['igst']),
            }
            for (supply_type, state_id), amounts in sorted(interstate.items())
            if not currency.is_zero(amounts['taxable_value']) or not currency.is_zero(amounts['igst'])
        ]
        return values, lines, warnings
