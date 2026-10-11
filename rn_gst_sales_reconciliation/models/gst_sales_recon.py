# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

SALE_TYPES = ('out_invoice', 'out_refund', 'out_receipt')
HEADS = ('igst', 'cgst', 'sgst', 'cess')
FINDINGS = [
    ('ledger_tax', 'Output GST posted outside invoices'),
    ('sequence_gap', 'Gap in invoice numbering'),
    ('cancelled', 'Cancelled invoice'),
    ('added_after_filing', 'Invoice not in filed GSTR-1'),
    ('removed_after_filing', 'Filed invoice no longer in books'),
    ('changed_after_filing', 'Invoice changed after filing'),
]
SEVERITY = {
    'ledger_tax': 'warning', 'sequence_gap': 'warning', 'cancelled': 'info',
    'added_after_filing': 'error', 'removed_after_filing': 'error', 'changed_after_filing': 'error',
}


class RnGstSalesRecon(models.Model):
    _name = 'rn.gst.sales.recon'
    _description = 'Sales Reconciliation'
    _inherit = ['mail.thread']
    _order = 'period_start desc, id desc'

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    gstin = fields.Char(string='GSTIN', required=True, default=lambda self: self.env.company.vat)
    financial_year = fields.Char(required=True, help='e.g. 2025-26')
    return_period = fields.Char(required=True, help='Month MM, e.g. 04 for April.')
    period_start = fields.Date(compute='_compute_period', store=True)
    period_end = fields.Date(compute='_compute_period', store=True)
    tolerance = fields.Monetary(default=1.0, currency_field='currency_id',
                                help='Differences up to this amount are not reported.')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Checked')], default='draft', tracking=True)
    filing_ref = fields.Char(string='Filed GSTR-1', readonly=True)
    books_taxable = fields.Monetary(string='Taxable in Books', readonly=True, currency_field='currency_id')
    books_tax = fields.Monetary(string='GST on Invoices', readonly=True, currency_field='currency_id')
    ledger_tax = fields.Monetary(string='Output GST in Ledger', readonly=True, currency_field='currency_id')
    filed_taxable = fields.Monetary(string='Taxable in Filed GSTR-1', readonly=True, currency_field='currency_id')
    filed_tax = fields.Monetary(string='GST in Filed GSTR-1', readonly=True, currency_field='currency_id')
    line_ids = fields.One2many('rn.gst.sales.recon.line', 'recon_id', string='Findings')
    error_count = fields.Integer(compute='_compute_counts', store=True)
    open_count = fields.Integer(string='Open Findings', compute='_compute_counts', store=True)
    checked_at = fields.Datetime(readonly=True)

    @api.depends('financial_year', 'return_period')
    def _compute_period(self):
        Period = self.env['rn.gst.filing.period']
        for rec in self:
            try:
                rec.period_start, rec.period_end = Period.compute_period_dates(
                    rec.financial_year, rec.return_period, 'monthly',
                ) if rec.financial_year and rec.return_period else (False, False)
            except ValidationError:
                rec.period_start = rec.period_end = False

    @api.depends('line_ids.severity', 'line_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.error_count = len(rec.line_ids.filtered(lambda l: l.severity == 'error'))
            rec.open_count = len(rec.line_ids.filtered(lambda l: l.state == 'open'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.sales.recon') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Books
    # ------------------------------------------------------------------

    def _rn_line_domain(self):
        self.ensure_one()
        return [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
        ]

    def _rn_gst_taxes(self):
        self.ensure_one()
        return self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id),
        ]).filtered(lambda t: t.l10n_in_gst_tax_type in HEADS)

    def _rn_output_tax_accounts(self):
        """Accounts that receive output GST: tax repartition accounts of the company's GST sale taxes."""
        self.ensure_one()
        taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id), ('type_tax_use', '=', 'sale'),
        ]).flatten_taxes_hierarchy().filtered(lambda t: t.l10n_in_gst_tax_type in HEADS)
        lines = taxes.invoice_repartition_line_ids | taxes.refund_repartition_line_ids
        return lines.filtered(lambda r: r.repartition_type == 'tax' and r.factor_percent > 0).account_id

    def _rn_books_by_move(self):
        """{move: {'taxable': x, 'tax': y}} for posted sales documents of the period, by invoice date."""
        self.ensure_one()
        books = defaultdict(lambda: {'taxable': 0.0, 'tax': 0.0})
        domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', SALE_TYPES),
            ('move_id.invoice_date', '>=', self.period_start),
            ('move_id.invoice_date', '<=', self.period_end),
        ]
        for move, balance in self.env['account.move.line']._read_group(
            domain + [('display_type', '=', 'product')], ['move_id'], ['balance:sum'],
        ):
            books[move]['taxable'] -= balance
        for move, balance in self.env['account.move.line']._read_group(
            # GST on the output tax accounts only: an export with IGST paid books +100% to IGST payable and
            # -100% to a refund asset, a reverse charge sale books both to the RCM control account.
            domain + [('display_type', '=', 'tax'), ('tax_line_id', 'in', self._rn_gst_taxes().ids),
                      ('account_id', 'in', self._rn_output_tax_accounts().ids)],
            ['move_id'], ['balance:sum'],
        ):
            books[move]['tax'] -= balance
        return books

    def _rn_filed(self):
        """The filed GSTR-1 of the period and {move: {'taxable', 'tax'}} as filed."""
        self.ensure_one()
        if 'rn.gst.filing' not in self.env:
            return False, {}
        filing = self.env['rn.gst.filing'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
            ('filing_type', '=', 'gstr1'),
            ('state', '=', 'filed'),
        ], limit=1)
        filed = defaultdict(lambda: {'taxable': 0.0, 'tax': 0.0, 'number': False})
        for line in filing.line_ids:
            entry = filed[line.move_id]
            entry['taxable'] += line.taxable_value
            entry['tax'] += line.cgst_amount + line.sgst_amount + line.igst_amount + line.cess_amount
            entry['number'] = entry['number'] or line.invoice_number
        return filing, filed

    def action_run(self):
        for rec in self:
            if not rec.period_start:
                raise UserError(_('Set a valid financial year (2025-26) and month (01 to 12).'))
            findings = rec._rn_findings()
            previous = {(l.move_id.id, l.code): l for l in rec.line_ids}
            for vals in findings:
                old = previous.get((vals.get('move_id') or False, vals['code']))
                if old and old.state != 'open':
                    vals.update(state=old.state, note=old.note)
            rec.write({
                'line_ids': [Command.clear()] + [Command.create(v) for v in findings],
                'state': 'done',
                'checked_at': fields.Datetime.now(),
            })
            rec.message_post(body=_('Sales check done: %(count)s finding(s), %(errors)s error(s).',
                                    count=len(findings), errors=rec.error_count))
        return True

    def _rn_findings(self):
        self.ensure_one()
        currency = self.currency_id
        findings = []

        def add(code, message, move=None, books=0.0, other=0.0):
            findings.append({
                'code': code, 'severity': SEVERITY[code], 'message': message,
                'move_id': move.id if move else False,
                'books_amount': books, 'other_amount': other, 'difference': books - other,
            })

        books = self._rn_books_by_move()
        self.books_taxable = sum(v['taxable'] for v in books.values())
        self.books_tax = sum(v['tax'] for v in books.values())

        # Ledger against invoices.
        accounts = self._rn_output_tax_accounts()
        ledger_lines = self.env['account.move.line'].search(self._rn_line_domain() + [('account_id', 'in', accounts.ids)])
        self.ledger_tax = -sum(ledger_lines.mapped('balance'))
        outside = defaultdict(float)
        for line in ledger_lines.filtered(lambda l: l.move_id.move_type == 'entry'):
            outside[line.move_id] -= line.balance
        for move, amount in outside.items():
            if currency.is_zero(amount):
                continue
            if amount > 0:
                message = _('%(move)s adds %(amount)s of output GST without a sales invoice: GSTR-1 will not show it.',
                            move=move.name, amount=currency.format(amount))
            else:
                message = _('%(move)s takes %(amount)s off the output GST accounts (set-off or adjustment).',
                            move=move.name, amount=currency.format(-amount))
            add('ledger_tax', message, move, books=amount)

        # Document series.
        sales = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id), ('move_type', 'in', SALE_TYPES),
            ('invoice_date', '>=', self.period_start), ('invoice_date', '<=', self.period_end),
            ('state', 'in', ('posted', 'cancel')),
        ])
        for move in sales.filtered(lambda m: m.state == 'posted' and m.made_sequence_gap):
            add('sequence_gap', _('Number gap before %s in its series.', move.name), move)
        for move in sales.filtered(lambda m: m.state == 'cancel' and m.name and m.name != '/'):
            add('cancelled', _('%s is cancelled: report it as cancelled in the GSTR-1 document summary.', move.name),
                move)

        # Books against the filed return.
        filing, filed = self._rn_filed()
        self.filing_ref = filing.display_name if filing else False
        self.filed_taxable = sum(v['taxable'] for v in filed.values())
        self.filed_tax = sum(v['tax'] for v in filed.values())
        if filing:
            for move, values in books.items():
                if move not in filed:
                    add('added_after_filing', _('%s is in the books but not in the filed GSTR-1: report it in the next '
                                                'return.', move.name), move, books=values['taxable'])
                    continue
                was = filed[move]
                if currency.compare_amounts(abs(values['taxable'] - was['taxable']), self.tolerance) > 0 or \
                        currency.compare_amounts(abs(values['tax'] - was['tax']), self.tolerance) > 0:
                    add('changed_after_filing', _(
                        '%(move)s changed after filing: taxable %(now)s now, %(was)s filed; GST %(tax_now)s now, '
                        '%(tax_was)s filed. Amend it in the next GSTR-1.',
                        move=move.name, now=currency.format(values['taxable']), was=currency.format(was['taxable']),
                        tax_now=currency.format(values['tax']), tax_was=currency.format(was['tax']),
                    ), move, books=values['taxable'], other=was['taxable'])
            for move, was in filed.items():
                if move and move in books:
                    continue
                label = move.name if move else was['number']
                add('removed_after_filing', _('%s was filed in GSTR-1 but is no longer a posted invoice of this month '
                                              'in the books.', label), move if move else None,
                    other=was['taxable'])
        return findings

    def action_open_filing(self):
        self.ensure_one()
        filing, _filed = self._rn_filed()
        if not filing:
            raise UserError(_('No filed GSTR-1 for this GSTIN and month.'))
        return {'type': 'ir.actions.act_window', 'res_model': filing._name, 'res_id': filing.id, 'view_mode': 'form'}


class RnGstSalesReconLine(models.Model):
    _name = 'rn.gst.sales.recon.line'
    _description = 'Sales Reconciliation Finding'
    _order = 'severity_rank, id'

    recon_id = fields.Many2one('rn.gst.sales.recon', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='recon_id.company_id', store=True)
    currency_id = fields.Many2one(related='recon_id.currency_id')
    move_id = fields.Many2one('account.move', string='Document', ondelete='set null', index=True)
    partner_id = fields.Many2one(related='move_id.commercial_partner_id', string='Partner')
    code = fields.Selection(FINDINGS, string='Finding', required=True)
    severity = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')], required=True)
    severity_rank = fields.Integer(compute='_compute_severity_rank', store=True)
    message = fields.Char(required=True)
    books_amount = fields.Monetary(string='Books', currency_field='currency_id')
    other_amount = fields.Monetary(string='Filed', currency_field='currency_id')
    difference = fields.Monetary(currency_field='currency_id')
    state = fields.Selection([('open', 'Open'), ('reviewed', 'Reviewed'), ('ignored', 'Ignored')], default='open',
                             required=True)
    note = fields.Char()

    @api.depends('severity')
    def _compute_severity_rank(self):
        rank = {'error': 0, 'warning': 1, 'info': 2}
        for line in self:
            line.severity_rank = rank.get(line.severity, 9)

    def action_reviewed(self):
        self.write({'state': 'reviewed'})
        return True

    def action_ignore(self):
        if self.filtered(lambda l: not l.note):
            raise UserError(_('Write a note before ignoring a finding.'))
        self.write({'state': 'ignored'})
        return True

    def action_reopen(self):
        self.write({'state': 'open'})
        return True

    def action_open_document(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('This finding has no document in Odoo.'))
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.move_id.id,
                'view_mode': 'form'}
