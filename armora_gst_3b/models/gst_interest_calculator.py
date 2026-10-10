# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError


class ArmoraGstInterestCalculator(models.AbstractModel):
    """GSTR-3B interest calculator (versioned).

    From Jan 2026 (GSTN advisory / Rule 88B(1) proviso):
    Interest = (Net Tax Liability - Minimum ECL balance from due date to debit date)
               × (days delayed / 365) × applicable rate

    System interest is a floor. Self-assessed may be higher, never lower via automation.
    """

    _name = 'armora.gst.interest.calculator'
    _description = 'Armora GST Interest Calculator'

    @api.model
    def _money(self, amount):
        return Decimal(str(amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @api.model
    def _resolve_rule(self, return_period_date=None, return_period=None):
        Rule = self.env['armora.gst.rule']
        on_date = return_period_date or date(2026, 1, 1)
        rule = Rule.find_applicable(
            'GSTR3B_INTEREST',
            on_date=on_date,
            return_period=return_period,
        )
        if not rule:
            raise UserError(_('No GSTR3B_INTEREST rule is applicable for the selected period.'))
        return rule

    @api.model
    def calculate(self, vals):
        """Calculate system minimum interest.

        vals keys:
          return_period, due_date, payment_date, net_tax_liability,
          interest_rate (optional), minimum_ecl_balance, tax_payment_details (optional dict)
        """
        data = vals or {}
        due_date = fields_date(data.get('due_date'))
        payment_date = fields_date(data.get('payment_date'))
        if not due_date or not payment_date:
            raise ValidationError(_('due_date and payment_date are required.'))
        if payment_date < due_date:
            # Early payment: no delay interest under this formula
            days_delayed = 0
        else:
            days_delayed = (payment_date - due_date).days

        return_period = data.get('return_period')
        period_date = due_date.replace(day=1)
        # Interest enhancement applies to delayed returns from Jan 2026 tax period
        rule = self._resolve_rule(return_period_date=period_date, return_period=return_period)
        cfg = rule.get_config()
        rate = Decimal(str(data.get('interest_rate') if data.get('interest_rate') is not None else cfg.get('default_rate', 0.18)))
        day_basis = Decimal(str(cfg.get('day_basis', 365)))
        formula = cfg.get('formula') or 'ecl_minimum'

        net_liability = self._money(data.get('net_tax_liability'))
        min_ecl = self._money(data.get('minimum_ecl_balance'))
        if min_ecl < 0:
            raise ValidationError(_('minimum_ecl_balance cannot be negative.'))

        if formula == 'ecl_minimum':
            taxable_base = max(net_liability - min_ecl, Decimal('0.00'))
        elif formula == 'simple':
            # Legacy/simple path kept for pre-2026 versioned rules only
            taxable_base = net_liability
        else:
            raise UserError(_('Unsupported interest formula version: %s') % formula)

        if days_delayed <= 0 or taxable_base <= 0:
            system_interest = self._money(0)
        else:
            system_interest = self._money(
                taxable_base * (Decimal(days_delayed) / day_basis) * rate
            )

        self_assessed = data.get('self_assessed_interest')
        if self_assessed is None:
            self_assessed_interest = system_interest
        else:
            self_assessed_interest = self._money(self_assessed)
            if self_assessed_interest < system_interest:
                raise ValidationError(_(
                    'Self-assessed interest (%(self)s) cannot be lower than system minimum interest (%(sys)s).'
                ) % {'self': self_assessed_interest, 'sys': system_interest})

        return {
            'computed_interest': float(system_interest),
            'system_minimum_interest': float(system_interest),
            'self_assessed_interest': float(self_assessed_interest),
            'interest_difference': float(self_assessed_interest - system_interest),
            'calculation_date': fields_date(data.get('calculation_date')) or date.today(),
            'calculation_version': rule.version,
            'days_delayed': days_delayed,
            'taxable_base': float(taxable_base),
            'interest_rate': float(rate),
            'formula': formula,
            'rule_id': rule.id,
        }

    @api.model
    def recompute(self, vals):
        """Recompute interest using latest rule parameters (portal RE-COMPUTE INTEREST parity)."""
        data = dict(vals or {})
        return_period = data.get('return_period')
        on_date = fields_date(data.get('due_date')) or date(2026, 1, 1)
        Rule = self.env['armora.gst.rule']
        recompute_rule = Rule.find_applicable(
            'GSTR3B_INTEREST_RECOMPUTE',
            on_date=on_date,
            return_period=return_period,
        )
        if recompute_rule and not recompute_rule.get_config().get('allow_recompute', True):
            raise UserError(_('Interest recompute is disabled for this period by GST rule configuration.'))
        result = self.calculate(data)
        result['recomputed'] = True
        if recompute_rule:
            result['recompute_rule_version'] = recompute_rule.version
        return result


def fields_date(value):
    from odoo import fields
    if not value:
        return False
    if isinstance(value, date):
        return value
    return fields.Date.to_date(value)
