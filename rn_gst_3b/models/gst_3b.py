# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RnGst3b(models.Model):
    _name = 'rn.gst.3b'
    _description = 'Armora GSTR-3B'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reporting_period desc, id desc'

    name = fields.Char(required=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    gstin = fields.Char(required=True)
    financial_year = fields.Char(required=True)
    return_period = fields.Char(required=True, help='Month 01-12')
    reporting_period = fields.Char(
        compute='_compute_reporting_period',
        store=True,
        help='YYYYMM',
    )
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    due_date = fields.Date(required=True)
    payment_date = fields.Date(string='Payment / Offset Date')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('computed', 'Computed'),
            ('filed', 'Filed'),
        ],
        default='draft',
        tracking=True,
    )

    net_tax_liability = fields.Monetary(currency_field='currency_id')
    minimum_ecl_balance = fields.Monetary(
        string='Minimum ECL Balance',
        currency_field='currency_id',
        help='Minimum Electronic Cash Ledger balance continuously available from due date to debit date.',
    )
    interest_rate = fields.Float(default=0.18)
    computed_interest = fields.Monetary(currency_field='currency_id', tracking=True)
    system_minimum_interest = fields.Monetary(currency_field='currency_id', tracking=True)
    self_assessed_interest = fields.Monetary(currency_field='currency_id', tracking=True)
    interest_difference = fields.Monetary(currency_field='currency_id')
    interest_calculation_date = fields.Date()
    interest_calculation_version = fields.Char()

    liability_breakup_ids = fields.One2many(
        'rn.gst.3b.liability.breakup',
        'filing_id',
        string='Tax Liability Breakup',
    )

    # ITC snapshot
    itc_opening_igst = fields.Monetary(currency_field='currency_id')
    itc_opening_cgst = fields.Monetary(currency_field='currency_id')
    itc_opening_sgst = fields.Monetary(currency_field='currency_id')
    itc_opening_cess = fields.Monetary(currency_field='currency_id')
    itc_available_igst = fields.Monetary(currency_field='currency_id')
    itc_available_cgst = fields.Monetary(currency_field='currency_id')
    itc_available_sgst = fields.Monetary(currency_field='currency_id')
    itc_available_cess = fields.Monetary(currency_field='currency_id')
    liability_igst = fields.Monetary(currency_field='currency_id')
    liability_cgst = fields.Monetary(currency_field='currency_id')
    liability_sgst = fields.Monetary(currency_field='currency_id')
    liability_cess = fields.Monetary(currency_field='currency_id')
    itc_utilized_igst = fields.Monetary(currency_field='currency_id')
    itc_utilized_cgst = fields.Monetary(currency_field='currency_id')
    itc_utilized_sgst = fields.Monetary(currency_field='currency_id')
    itc_utilized_cess = fields.Monetary(currency_field='currency_id')
    itc_remaining_igst = fields.Monetary(currency_field='currency_id')
    itc_remaining_cgst = fields.Monetary(currency_field='currency_id')
    itc_remaining_sgst = fields.Monetary(currency_field='currency_id')
    itc_remaining_cess = fields.Monetary(currency_field='currency_id')
    cash_payable_igst = fields.Monetary(currency_field='currency_id')
    cash_payable_cgst = fields.Monetary(currency_field='currency_id')
    cash_payable_sgst = fields.Monetary(currency_field='currency_id')
    cash_payable_cess = fields.Monetary(currency_field='currency_id')
    itc_utilization_version = fields.Char()
    itc_utilization_audit = fields.Text()

    @api.depends('financial_year', 'return_period')
    def _compute_reporting_period(self):
        Period = self.env['rn.gst.filing.period']
        for rec in self:
            if not rec.financial_year or not rec.return_period:
                rec.reporting_period = False
                continue
            try:
                start, _end = Period.compute_period_dates(
                    rec.financial_year, rec.return_period, 'monthly'
                )
                rec.reporting_period = '%04d%02d' % (start.year, start.month)
            except (ValueError, TypeError, ValidationError):
                rec.reporting_period = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.3b') or 'GSTR3B'
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        chatter_ok = {
            'message_follower_ids', 'activity_ids', 'message_ids', '__last_update',
        }
        protected = set(vals.keys()) - chatter_ok
        for rec in self:
            if (
                rec.state == 'filed'
                and protected
                and not self.env.context.get('rn_force_3b_write')
                and not self.env.su
            ):
                raise UserError(_('Filed GSTR-3B records are read-only.'))
        if 'self_assessed_interest' in vals:
            for rec in self:
                proposed = vals['self_assessed_interest']
                minimum = vals.get('system_minimum_interest', rec.system_minimum_interest) or 0.0
                if proposed is not None and proposed < minimum:
                    raise ValidationError(_(
                        'Self-assessed interest cannot be lower than system minimum interest.'
                    ))
        return super().write(vals)

    def _rn_interest_calc_payload(self):
        self.ensure_one()
        return {
            'return_period': self.reporting_period,
            'due_date': self.due_date,
            'payment_date': self.payment_date,
            'net_tax_liability': self.net_tax_liability,
            'interest_rate': self.interest_rate,
            'minimum_ecl_balance': self.minimum_ecl_balance,
            'self_assessed_interest': self.self_assessed_interest or None,
        }

    def action_compute_interest(self):
        Calculator = self.env['rn.gst.interest.calculator']
        for rec in self:
            if not rec.payment_date:
                raise UserError(_('Set Payment / Offset Date before computing interest.'))
            result = Calculator.calculate(rec._rn_interest_calc_payload())
            rec.write({
                'computed_interest': result['computed_interest'],
                'system_minimum_interest': result['system_minimum_interest'],
                'self_assessed_interest': result['self_assessed_interest'],
                'interest_difference': result['interest_difference'],
                'interest_calculation_date': result['calculation_date'],
                'interest_calculation_version': result['calculation_version'],
                'state': 'computed' if rec.state == 'draft' else rec.state,
            })
            rec.message_post(body=_(
                'Interest computed (version %(ver)s). System minimum: %(sys)s. Self-assessed: %(self)s.',
                ver=result['calculation_version'],
                sys=result['system_minimum_interest'],
                self=result['self_assessed_interest'],
            ))
        return True

    def action_recompute_interest(self):
        """Refresh system minimum interest; keep or raise self-assessed only."""
        Calculator = self.env['rn.gst.interest.calculator']
        for rec in self:
            if not rec.payment_date:
                raise UserError(_('Set Payment / Offset Date before recomputing interest.'))
            payload = rec._rn_interest_calc_payload()
            previous_self = rec.self_assessed_interest
            payload['self_assessed_interest'] = None
            result = Calculator.recompute(payload)
            new_self = max(result['system_minimum_interest'], previous_self or 0.0)
            if previous_self and previous_self > result['system_minimum_interest']:
                new_self = previous_self
            rec.write({
                'computed_interest': result['computed_interest'],
                'system_minimum_interest': result['system_minimum_interest'],
                'self_assessed_interest': new_self,
                'interest_difference': new_self - result['system_minimum_interest'],
                'interest_calculation_date': result['calculation_date'],
                'interest_calculation_version': result['calculation_version'],
                'state': 'computed' if rec.state == 'draft' else rec.state,
            })
            rec.message_post(body=_(
                'Interest recomputed (version %(ver)s). New system minimum: %(sys)s. Self-assessed: %(self)s.',
                ver=result['calculation_version'],
                sys=result['system_minimum_interest'],
                self=new_self,
            ))
        return True

    def action_compute_itc_utilization(self):
        Engine = self.env['rn.gst.itc.utilization']
        for rec in self:
            result = Engine.utilize({
                'on_date': rec.period_start,
                'return_period': rec.reporting_period,
                'opening_itc': {
                    'igst': rec.itc_opening_igst,
                    'cgst': rec.itc_opening_cgst,
                    'sgst': rec.itc_opening_sgst,
                    'cess': rec.itc_opening_cess,
                },
                'itc_available': {
                    'igst': rec.itc_available_igst,
                    'cgst': rec.itc_available_cgst,
                    'sgst': rec.itc_available_sgst,
                    'cess': rec.itc_available_cess,
                },
                'liabilities': {
                    'igst': rec.liability_igst,
                    'cgst': rec.liability_cgst,
                    'sgst': rec.liability_sgst,
                    'cess': rec.liability_cess,
                },
            })
            util = result['itc_utilized']
            rem = result['itc_remaining']
            cash = result['cash_payable']
            rec.write({
                'itc_utilized_igst': util['igst'],
                'itc_utilized_cgst': util['cgst'],
                'itc_utilized_sgst': util['sgst'],
                'itc_utilized_cess': util['cess'],
                'itc_remaining_igst': rem['igst'],
                'itc_remaining_cgst': rem['cgst'],
                'itc_remaining_sgst': rem['sgst'],
                'itc_remaining_cess': rem['cess'],
                'cash_payable_igst': cash['igst'],
                'cash_payable_cgst': cash['cgst'],
                'cash_payable_sgst': cash['sgst'],
                'cash_payable_cess': cash['cess'],
                'itc_utilization_version': result['rule_version'],
                'itc_utilization_audit': str(result['steps']),
                'state': 'computed' if rec.state == 'draft' else rec.state,
            })
            rec.message_post(body=_(
                'ITC utilization computed using rule version %s.',
                result['rule_version'],
            ))
        return True

    def action_mark_filed(self):
        for rec in self:
            rec.state = 'filed'
            rec.message_post(body=_('GSTR-3B marked as filed (read-only).'))
        return True
