# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

TAX_HEADS = ('igst', 'cgst', 'sgst')


class ArmoraGstTdsTcsPeriod(models.Model):
    """GST TDS and TCS credits of one month, as expected from invoices and as
    reported by deductors and e-commerce operators in GSTR-2X."""

    _name = 'armora.gst.tds.tcs.period'
    _description = 'GST TDS/TCS Month'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_start desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    gstin = fields.Char(required=True, tracking=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    return_period = fields.Char(required=True, tracking=True, help='Month MM, e.g. 04 for April.')
    period_start = fields.Date(compute='_compute_period', store=True)
    period_end = fields.Date(compute='_compute_period', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('closed', 'Closed'),
    ], default='draft', required=True, tracking=True, copy=False)
    credit_ids = fields.One2many('armora.gst.tds.tcs.credit', 'period_id', string='Credits')
    expected_total = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    reported_total = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    accepted_total = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    mismatch_count = fields.Integer(compute='_compute_totals')

    _armora_gst_tds_tcs_period_uniq = models.Constraint(
        'unique(company_id, gstin, financial_year, return_period)',
        "A TDS/TCS month already exists for this company, GSTIN and month.",
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

    @api.depends('credit_ids.expected_total', 'credit_ids.reported_total', 'credit_ids.state', 'credit_ids.match_state')
    def _compute_totals(self):
        for rec in self:
            credits = rec.credit_ids
            rec.expected_total = sum(credits.mapped('expected_total'))
            rec.reported_total = sum(credits.mapped('reported_total'))
            rec.accepted_total = sum(credits.filtered(lambda c: c.state == 'accepted').mapped('claim_total'))
            rec.mismatch_count = len(credits.filtered(lambda c: c.match_state in ('mismatch', 'reported_only')))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('armora.gst.tds.tcs.period') or _('New')
            if not vals.get('gstin'):
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                vals['gstin'] = company.vat or ''
        return super().create(vals_list)

    def action_compute_expected(self):
        """Expected GST TDS (customers that deduct it) and TCS (e-commerce operators)
        from the month's posted customer invoices. Reported amounts and decisions are kept."""
        for rec in self:
            if rec.state == 'closed':
                raise UserError(_('This month is closed.'))
            expected = rec._armora_expected_credits()
            by_key = {(c.credit_type, c.partner_id.id): c for c in rec.credit_ids}
            for key, vals in expected.items():
                credit = by_key.pop(key, None)
                if credit:
                    if credit.state == 'pending':
                        credit.write(vals)
                else:
                    rec.write({'credit_ids': [Command.create(dict(vals, credit_type=key[0], partner_id=key[1]))]})
            # Credits with nothing expected any more keep their reported amounts only.
            for credit in by_key.values():
                if credit.state == 'pending':
                    credit.write(dict(dict.fromkeys(
                        ['expected_taxable'] + ['expected_%s' % h for h in TAX_HEADS], 0.0,
                    ), invoice_ids=[Command.clear()]))
            rec.state = 'computed'
            rec.message_post(body=_('Expected TDS/TCS computed: %s.', rec.expected_total))
        return True

    def _armora_expected_credits(self):
        self.ensure_one()
        company = self.company_id
        currency = self.currency_id
        invoices = self.env['account.move'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('invoice_date', '>=', self.period_start),
            ('invoice_date', '<=', self.period_end),
            '|',
            ('commercial_partner_id.armora_gst_tds_deductor', '=', True),
            ('commercial_partner_id.armora_gst_tcs_operator', '=', True),
        ])
        result = {}

        def bucket(credit_type, partner):
            return result.setdefault((credit_type, partner.id), {
                'expected_taxable': 0.0, 'expected_igst': 0.0, 'expected_cgst': 0.0, 'expected_sgst': 0.0,
                'invoice_ids': [Command.clear()],
                'deductor_gstin': partner.vat or False,
            })

        for move in invoices:
            partner = move.commercial_partner_id
            taxable = move.amount_untaxed_signed
            # Same state as the company: half CGST, half SGST; otherwise IGST.
            intra = move.l10n_in_state_id and move.l10n_in_state_id == company.state_id
            targets = []
            if partner.armora_gst_tds_deductor and move.move_type == 'out_invoice' \
                    and currency.compare_amounts(abs(taxable), company.armora_gst_tds_threshold) > 0:
                targets.append(('tds', company.armora_gst_tds_rate))
            if partner.armora_gst_tcs_operator:
                # TCS runs on the net value: credit notes reduce it.
                targets.append(('tcs', company.armora_gst_tcs_rate))
            for credit_type, rate in targets:
                vals = bucket(credit_type, partner)
                tax = taxable * rate / 100.0
                vals['expected_taxable'] += taxable
                if intra:
                    vals['expected_cgst'] += tax / 2.0
                    vals['expected_sgst'] += tax / 2.0
                else:
                    vals['expected_igst'] += tax
                vals['invoice_ids'].append(Command.link(move.id))
        for vals in result.values():
            for name in ('expected_taxable', 'expected_igst', 'expected_cgst', 'expected_sgst'):
                vals[name] = currency.round(vals[name])
        return result

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import GSTR-2X'),
            'res_model': 'armora.gst.tds.tcs.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_period_id': self.id},
        }

    def action_accept_matched(self):
        for rec in self:
            rec.credit_ids.filtered(lambda c: c.state == 'pending' and c.match_state == 'matched').action_accept()
        return True

    def action_close(self):
        self.write({'state': 'closed'})
        return True

    def action_reopen(self):
        self.write({'state': 'computed'})
        return True


class ArmoraGstTdsTcsCredit(models.Model):
    _name = 'armora.gst.tds.tcs.credit'
    _description = 'GST TDS/TCS Credit'
    _order = 'credit_type, partner_id'

    period_id = fields.Many2one('armora.gst.tds.tcs.period', string='Month', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='period_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='period_id.currency_id')
    credit_type = fields.Selection([
        ('tds', 'GST TDS (section 51)'),
        ('tcs', 'GST TCS (section 52)'),
    ], string='Type', required=True)
    partner_id = fields.Many2one('res.partner', string='Deductor / Operator', index=True)
    deductor_gstin = fields.Char(string='Deductor GSTIN')
    invoice_ids = fields.Many2many('account.move', string='Invoices')
    expected_taxable = fields.Monetary(currency_field='currency_id', readonly=True)
    expected_igst = fields.Monetary(string='Expected IGST', currency_field='currency_id', readonly=True)
    expected_cgst = fields.Monetary(string='Expected CGST', currency_field='currency_id', readonly=True)
    expected_sgst = fields.Monetary(string='Expected SGST', currency_field='currency_id', readonly=True)
    expected_total = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    reported_taxable = fields.Monetary(string='Reported Taxable', currency_field='currency_id',
                                       help='As reported by the deductor or operator in GSTR-2X.')
    reported_igst = fields.Monetary(string='Reported IGST', currency_field='currency_id')
    reported_cgst = fields.Monetary(string='Reported CGST', currency_field='currency_id')
    reported_sgst = fields.Monetary(string='Reported SGST', currency_field='currency_id')
    reported_total = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    difference = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id',
                                 help='Reported minus expected.')
    claim_total = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id',
                                  help='Amount booked on acceptance: the reported amount, or the expected one when nothing is reported.')
    match_state = fields.Selection([
        ('expected_only', 'Not reported yet'),
        ('reported_only', 'Reported, not expected'),
        ('matched', 'Matched'),
        ('mismatch', 'Mismatch'),
    ], compute='_compute_totals', store=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    notes = fields.Char()

    @api.depends('expected_igst', 'expected_cgst', 'expected_sgst', 'reported_igst', 'reported_cgst', 'reported_sgst',
                 'period_id.company_id.armora_gst_recon_tolerance')
    def _compute_totals(self):
        for credit in self:
            expected = sum(credit['expected_%s' % h] for h in TAX_HEADS)
            reported = sum(credit['reported_%s' % h] for h in TAX_HEADS)
            credit.expected_total = expected
            credit.reported_total = reported
            credit.difference = reported - expected
            credit.claim_total = reported or expected
            tolerance = credit.company_id.armora_gst_recon_tolerance or 0.0
            if not reported:
                credit.match_state = 'expected_only'
            elif not expected:
                credit.match_state = 'reported_only'
            elif all(abs(credit['reported_%s' % h] - credit['expected_%s' % h]) <= tolerance for h in TAX_HEADS):
                credit.match_state = 'matched'
            else:
                credit.match_state = 'mismatch'

    def action_accept(self):
        """Accept the credit (as in GSTR-2X) and, when an account and journal are set,
        book it against the customer's receivable."""
        for credit in self:
            if credit.state != 'pending':
                continue
            company = credit.company_id
            move = self.env['account.move']
            if company.armora_gst_tds_tcs_account_id and company.armora_gst_tds_tcs_journal_id and credit.claim_total:
                if not credit.partner_id:
                    raise UserError(_('Set the deductor or operator on the credit before accepting it.'))
                label = _('%(type)s credit %(period)s %(gstin)s', type=dict(
                    credit._fields['credit_type']._description_selection(self.env))[credit.credit_type],
                    period=credit.period_id.name, gstin=credit.deductor_gstin or '')
                receivable = credit.partner_id.with_company(company).property_account_receivable_id
                move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'company_id': company.id,
                    'journal_id': company.armora_gst_tds_tcs_journal_id.id,
                    'date': credit.period_id.period_end,
                    'ref': label,
                    'line_ids': [
                        Command.create({
                            'name': label, 'account_id': company.armora_gst_tds_tcs_account_id.id,
                            'debit': credit.claim_total, 'partner_id': credit.partner_id.id,
                        }),
                        Command.create({
                            'name': label, 'account_id': receivable.id,
                            'credit': credit.claim_total, 'partner_id': credit.partner_id.id,
                        }),
                    ],
                })
                move.action_post()
            credit.write({'state': 'accepted', 'move_id': move.id or False})
            credit.period_id.message_post(body=_(
                'Accepted %(type)s credit of %(amount)s from %(partner)s.',
                type=credit.credit_type.upper(), amount=credit.claim_total,
                partner=credit.partner_id.display_name or credit.deductor_gstin,
            ))
        return True

    def action_reject(self):
        self.filtered(lambda c: c.state == 'pending').write({'state': 'rejected'})
        return True

    def action_reset(self):
        for credit in self:
            if credit.move_id and credit.move_id.state == 'posted':
                raise UserError(_('Reverse journal entry %s before resetting the credit.', credit.move_id.name))
            credit.write({'state': 'pending', 'move_id': False})
        return True
