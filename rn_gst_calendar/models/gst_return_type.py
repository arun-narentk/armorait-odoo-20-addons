# -*- coding: utf-8 -*-
import calendar

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

REGISTRATION_TYPES = ('regular', 'composition', 'casual', 'sez', 'isd', 'other')


class RnGstReturnType(models.Model):
    _name = 'rn.gst.return.type'
    _description = 'GST Return Type'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer()
    description = fields.Text(translate=True)
    rule_ids = fields.One2many('rn.gst.due.rule', 'return_type_id', string='Due-Date Rules')

    _rn_gst_return_type_code_uniq = models.Constraint('unique(code)', "The return code must be unique.")


class RnGstDueRule(models.Model):
    """When a return is due, for which registrations, from which date.

    A rule applies to a registration when its type is listed, its filing frequency
    matches and (if set) its state code is listed. The due date is ``due_day`` of the
    month that is ``due_month_offset`` months after the end of the period.
    """

    _name = 'rn.gst.due.rule'
    _description = 'GST Due-Date Rule'
    _order = 'return_type_id, effective_from desc, id'

    return_type_id = fields.Many2one('rn.gst.return.type', required=True, ondelete='cascade', index=True)
    active = fields.Boolean(default=True)
    registration_types = fields.Char(
        required=True, default='regular,sez,casual',
        help='Comma separated registration types the rule applies to: ' + ', '.join(REGISTRATION_TYPES),
    )
    filer_frequency = fields.Selection([
        ('any', 'Any'),
        ('monthly', 'Monthly filers'),
        ('quarterly', 'Quarterly (QRMP) filers'),
    ], required=True, default='any')
    period_frequency = fields.Selection([
        ('monthly', 'Month'),
        ('quarterly', 'Quarter'),
        ('annual', 'Financial year'),
    ], string='One Return Per', required=True, default='monthly')
    skip_quarter_end = fields.Boolean(
        string='Skip Last Month of Quarter',
        help='For PMT-06: due only in the first two months of each quarter.',
    )
    needs_gstr9c = fields.Boolean(string='Only GSTINs Filing GSTR-9C')
    state_codes = fields.Char(
        help='Comma separated GST state codes (e.g. 27,29). Empty means all states.',
    )
    due_month_offset = fields.Integer(string='Months After Period', required=True, default=1)
    due_day = fields.Integer(string='Due Day', required=True, default=20)
    effective_from = fields.Date(required=True, default='2017-07-01')
    effective_to = fields.Date()
    note = fields.Char(help='Source of the rule, e.g. the notification number.')

    @api.constrains('due_day', 'due_month_offset')
    def _check_due(self):
        for rule in self:
            if not 1 <= rule.due_day <= 31 or rule.due_month_offset < 0:
                raise ValidationError(_('Due day must be 1 to 31 and months after period cannot be negative.'))

    @api.constrains('registration_types')
    def _check_registration_types(self):
        for rule in self:
            unknown = set(rule._rn_types()) - set(REGISTRATION_TYPES)
            if unknown:
                raise ValidationError(_('Unknown registration types: %s', ', '.join(sorted(unknown))))

    @api.depends('return_type_id', 'filer_frequency', 'due_day', 'state_codes')
    def _compute_display_name(self):
        for rule in self:
            name = '%s: day %s' % (rule.return_type_id.name, rule.due_day)
            if rule.filer_frequency != 'any':
                name += ' (%s)' % dict(self._fields['filer_frequency']._description_selection(self.env))[rule.filer_frequency]
            if rule.state_codes:
                name += ' [%s]' % rule.state_codes
            rule.display_name = name

    def _rn_types(self):
        self.ensure_one()
        return [t.strip() for t in (self.registration_types or '').split(',') if t.strip()]

    def _rn_states(self):
        self.ensure_one()
        return [s.strip().zfill(2) for s in (self.state_codes or '').split(',') if s.strip()]

    def _rn_applies_to(self, registration):
        self.ensure_one()
        if registration.registration_type not in self._rn_types():
            return False
        if self.filer_frequency != 'any' and self.filer_frequency != registration.rn_filing_frequency:
            return False
        if self.needs_gstr9c and not registration.rn_gstr9c_required:
            return False
        states = self._rn_states()
        return not states or (registration.state_code or '').zfill(2) in states

    def _rn_in_force(self, period_end):
        self.ensure_one()
        return self.effective_from <= period_end and (not self.effective_to or period_end <= self.effective_to)

    def _rn_due_date(self, period_end):
        self.ensure_one()
        month = period_end + relativedelta(months=self.due_month_offset)
        last_day = calendar.monthrange(month.year, month.month)[1]
        return month.replace(day=min(self.due_day, last_day))

    def _rn_periods(self, financial_year):
        """(return_period, period_start, period_end) of the rule's periods in a financial year."""
        self.ensure_one()
        Period = self.env['rn.gst.filing.period']
        if self.period_frequency == 'annual':
            start_year = Period.fy_start_year(financial_year)
            return [('FY', fields.Date.to_date('%s-04-01' % start_year), fields.Date.to_date('%s-03-31' % (start_year + 1)))]
        if self.period_frequency == 'quarterly':
            return [(q, *Period.compute_period_dates(financial_year, q, 'quarterly')) for q in ('Q1', 'Q2', 'Q3', 'Q4')]
        periods = []
        for month in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3):
            if self.skip_quarter_end and month in (6, 9, 12, 3):
                continue
            code = '%02d' % month
            periods.append((code, *Period.compute_period_dates(financial_year, code, 'monthly')))
        return periods
