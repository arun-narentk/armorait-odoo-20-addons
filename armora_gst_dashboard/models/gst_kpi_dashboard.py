# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..services import gst_dashboard_service as svc

SALE_TYPES = ('out_invoice', 'out_refund')
PURCHASE_TYPES = ('in_invoice', 'in_refund')
TAX_HEADS = ('igst', 'cgst', 'sgst', 'cess')
TREND_MONTHS = 6

# Progress of a return for the health score, by state.
GSTR1_PROGRESS = {
    'draft': 10, 'data_loaded': 30, 'validated': 55, 'generated': 75, 'submitted': 90, 'filed': 100,
}
GSTR3B_PROGRESS = {'draft': 30, 'computed': 70, 'filed': 100}


def _tax_head(group_name):
    name = (group_name or '').upper()
    for head in TAX_HEADS:
        if head.upper() in name:
            return head
    return False


class ArmoraGstDashboard(models.Model):
    _inherit = 'armora.gst.dashboard'

    @api.model
    def get_kpi_dashboard_data(self, financial_year=None, return_period=None):
        """Payload of the KPI dashboard client action for the current company."""
        self.check_access('read')
        Period = self.env['armora.gst.period']
        today = fields.Date.context_today(self)
        financial_year = financial_year or Period.current_financial_year(today)
        return_period = return_period or '%02d' % today.month
        try:
            date_from, date_to = Period.compute_period_dates(financial_year, return_period, 'monthly')
        except ValidationError:
            financial_year = Period.current_financial_year(today)
            return_period = '%02d' % today.month
            date_from, date_to = Period.compute_period_dates(financial_year, return_period, 'monthly')

        company = self.env.company
        prev_from = date_from - relativedelta(months=1)
        prev_to = date_from - relativedelta(days=1)
        current = self._armora_kpi_accounting(company, date_from, date_to)
        previous = self._armora_kpi_accounting(company, prev_from, prev_to)

        filters = {
            'company_id': company.id,
            'gstin': False,
            'financial_year': financial_year,
            'return_period': return_period,
            'date_from': date_from,
            'date_to': date_to,
        }
        suite = svc.get_dashboard_data(self.env, filters)
        availability = suite['module_availability']
        deadlines = self._armora_kpi_deadlines(company, financial_year, return_period, date_to, availability, today)

        start_year = Period.fy_start_year(Period.current_financial_year(today))
        return {
            'company': {
                'name': company.name,
                'gstin': company.vat or '',
                'currency_id': company.currency_id.id,
            },
            'filters': {
                'financial_year': financial_year,
                'return_period': return_period,
                'fy_options': ['%d-%02d' % (year, (year + 1) % 100) for year in range(start_year, start_year - 3, -1)],
                'period_options': ['%02d' % month for month in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)],
            },
            'period': {
                'date_from': fields.Date.to_string(date_from),
                'date_to': fields.Date.to_string(date_to),
            },
            'kpis': current['kpis'],
            'previous_kpis': previous['kpis'],
            'output_split': current['output_split'],
            'input_split': current['input_split'],
            'trend': self._armora_kpi_trend(company, date_from),
            'top_customers': self._armora_kpi_top_customers(company, date_from, date_to),
            'deadlines': deadlines,
            'health': self._armora_kpi_health(suite, deadlines),
            'availability': availability,
            'filing': {'kpis': suite['filing']['kpis'], 'rows': suite['filing']['rows'][:6]},
            'reconciliation_2b': {'kpis': suite['reconciliation_2b']['kpis']},
            'invoice_validation': {'kpis': suite['invoice_validation']['kpis']},
            'einvoice': {'kpis': suite['einvoice']['kpis']},
            'ewaybill': {'kpis': suite['ewaybill']['kpis']},
        }

    @api.model
    def _armora_kpi_accounting(self, company, date_from, date_to):
        Move = self.env['account.move']
        move_domain = [
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        kpis = {
            'sales_taxable': 0.0, 'purchase_taxable': 0.0,
            'invoice_count': 0, 'bill_count': 0, 'credit_note_count': 0,
            'output_tax': 0.0, 'input_tax': 0.0,
        }
        groups = Move._read_group(
            move_domain + [('move_type', 'in', SALE_TYPES + PURCHASE_TYPES)],
            ['move_type'], ['__count', 'amount_untaxed_signed:sum'],
        )
        for move_type, count, untaxed in groups:
            if move_type in SALE_TYPES:
                kpis['sales_taxable'] += untaxed
            else:
                # Vendor bills are signed negative; show purchases as a positive value.
                kpis['purchase_taxable'] -= untaxed
            if move_type == 'out_invoice':
                kpis['invoice_count'] += count
            elif move_type == 'in_invoice':
                kpis['bill_count'] += count
            elif move_type == 'out_refund':
                kpis['credit_note_count'] += count

        output_split = dict.fromkeys(TAX_HEADS, 0.0)
        input_split = dict.fromkeys(TAX_HEADS, 0.0)
        for (head,), output, tax_input in self._armora_kpi_gst_lines(company, date_from, date_to, []):
            output_split[head] += output
            input_split[head] += tax_input
        kpis['output_tax'] = sum(output_split.values())
        kpis['input_tax'] = sum(input_split.values())
        kpis['net_payable'] = kpis['output_tax'] - kpis['input_tax']
        return {'kpis': kpis, 'output_split': output_split, 'input_split': input_split}

    @api.model
    def _armora_kpi_gst_lines(self, company, date_from, date_to, groupby):
        """Yield (group key + tax head, output GST, input GST) from posted tax lines.

        Output GST follows the GST tags Odoo puts on sale tax lines: IGST paid on
        exports and SEZ supplies is tagged once, a supply under LUT is tagged on
        both of its +100%/-100% lines and nets to zero. Tax on reverse charge
        sales is the buyer's liability. On purchases, the +100% lines are input
        tax credit and the -100% line of a reverse charge tax is tax we owe.
        """
        gst_tags = self.env['account.account.tag']
        for xmlid in ('tax_tag_igst', 'tax_tag_cgst', 'tax_tag_sgst', 'tax_tag_cess'):
            gst_tags |= self.env.ref('l10n_in.%s' % xmlid, raise_if_not_found=False) or gst_tags.browse()
        base = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('tax_line_id', '!=', False),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        queries = (
            ([('move_id.move_type', 'in', SALE_TYPES), ('tax_tag_ids', 'in', gst_tags.ids),
              ('tax_line_id.l10n_in_reverse_charge', '=', False)], -1, 0),
            ([('move_id.move_type', 'in', PURCHASE_TYPES), ('tax_repartition_line_id.factor_percent', '<', 0),
              ('tax_line_id.l10n_in_reverse_charge', '=', True)], -1, 0),
            ([('move_id.move_type', 'in', PURCHASE_TYPES), ('tax_repartition_line_id.factor_percent', '>', 0)], 0, 1),
        )
        for extra, output_sign, input_sign in queries:
            for *keys, group, balance in self.env['account.move.line']._read_group(
                base + extra, groupby + ['tax_group_id'], ['balance:sum'],
            ):
                head = _tax_head(group.name)
                if head:
                    yield (*keys, head), output_sign * balance, input_sign * balance

    @api.model
    def _armora_kpi_trend(self, company, date_from):
        start = date_from - relativedelta(months=TREND_MONTHS - 1)
        end = date_from + relativedelta(months=1, days=-1)
        months = [start + relativedelta(months=i) for i in range(TREND_MONTHS)]
        output = dict.fromkeys(months, 0.0)
        tax_input = dict.fromkeys(months, 0.0)
        for (month, _head), out_amount, in_amount in self._armora_kpi_gst_lines(company, start, end, ['invoice_date:month']):
            if month in output:
                output[month] += out_amount
                tax_input[month] += in_amount
        return {
            'months': [fields.Date.to_string(month) for month in months],
            'output_tax': [output[month] for month in months],
            'input_tax': [tax_input[month] for month in months],
        }

    @api.model
    def _armora_kpi_top_customers(self, company, date_from, date_to, limit=5):
        groups = self.env['account.move']._read_group(
            [
                ('company_id', '=', company.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', SALE_TYPES),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
            ],
            ['partner_id'],
            ['amount_untaxed_signed:sum', 'amount_tax_signed:sum'],
            order='amount_untaxed_signed:sum desc',
            limit=limit,
        )
        return [{
            'id': partner.id,
            'name': partner.display_name,
            'gstin': partner.vat or '',
            'taxable': untaxed,
            'tax': tax,
        } for partner, untaxed, tax in groups if partner]

    @api.model
    def _armora_kpi_deadlines(self, company, financial_year, return_period, date_to, availability, today):
        """Monthly filer due dates: GSTR-1 on the 11th and GSTR-3B on the 20th of the next month."""
        next_month = date_to + relativedelta(days=1)
        deadlines = []
        returns = [
            ('GSTR-1', next_month.replace(day=11), 'filing', 'armora.gst.filing', [('filing_type', '=', 'gstr1')], ('submitted', 'filed')),
            ('GSTR-3B', next_month.replace(day=20), 'gstr3b', 'armora.gst.3b', [], ('filed',)),
        ]
        for code, due, module_key, model_name, extra_domain, done_states in returns:
            record = None
            if availability.get(module_key) and model_name in self.env:
                gstin_domain = [('gstin', '=', company.vat.upper())] if company.vat else []
                record = svc.aggregate_model(self.env, model_name).search([
                    ('company_id', '=', company.id),
                    ('financial_year', '=', financial_year),
                    ('return_period', '=', return_period),
                ] + gstin_domain + extra_domain, limit=1)
            if record:
                state_label = dict(record._fields['state']._description_selection(self.env)).get(record.state)
            done = bool(record) and record.state in done_states
            deadlines.append({
                'code': code,
                'due_date': fields.Date.to_string(due),
                'days_left': (due - today).days,
                'tracked': bool(availability.get(module_key)),
                'done': done,
                'state': record.state if record else False,
                'state_label': state_label if record else False,
                'res_model': model_name,
                'res_id': record.id if record else False,
            })
        return deadlines

    @api.model
    def _armora_kpi_health(self, suite, deadlines):
        parts = []
        for deadline in deadlines:
            if not deadline['tracked']:
                continue
            progress = GSTR1_PROGRESS if deadline['code'] == 'GSTR-1' else GSTR3B_PROGRESS
            parts.append({
                'label': '%s progress' % deadline['code'],
                'value': progress.get(deadline['state'], 0),
            })
        recon = suite['reconciliation_2b']['kpis']
        if recon:
            checked = sum(recon.get(key) or 0 for key in ('exact_matches', 'mismatches', 'missing_in_books', 'missing_in_2b'))
            if checked:
                parts.append({
                    'label': 'GSTR-2B match rate',
                    'value': round(100.0 * (recon.get('exact_matches') or 0) / checked),
                })
        filing = suite['filing']['kpis']
        if filing.get('filing_count'):
            errors = filing.get('filing_errors') or 0
            parts.append({'label': 'Filings without errors', 'value': max(0, 100 - 10 * errors)})
        score = round(sum(part['value'] for part in parts) / len(parts)) if parts else None
        return {'score': score, 'parts': parts}
