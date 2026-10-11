# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

# Return code -> (model, filing type or None) of the Armora record that files it.
FILING_SOURCES = {
    'GSTR1': ('rn.gst.filing', 'gstr1'),
    'GSTR9': ('rn.gst.filing', 'gstr9'),
    'GSTR3B': ('rn.gst.3b', None),
}


class RnGstObligation(models.Model):
    """One GST return one GSTIN has to file for one period."""

    _name = 'rn.gst.obligation'
    _description = 'GST Return Due'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, return_type_id, id'

    registration_id = fields.Many2one('rn.gst.registration', string='GST Registration', required=True, index=True,
                                      ondelete='cascade')
    company_id = fields.Many2one(related='registration_id.company_id', store=True, index=True)
    gstin = fields.Char(related='registration_id.gstin', store=True)
    return_type_id = fields.Many2one('rn.gst.return.type', string='Return', required=True, index=True)
    rule_id = fields.Many2one('rn.gst.due.rule', required=True, ondelete='restrict')
    color = fields.Integer(related='return_type_id.color')
    financial_year = fields.Char(required=True, index=True)
    return_period = fields.Char(string='Period', required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    rule_due_date = fields.Date(string='Normal Due Date', readonly=True)
    due_date = fields.Date(required=True, index=True, tracking=True)
    extension_id = fields.Many2one('rn.gst.due.extension', readonly=True, ondelete='set null')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('filed', 'Filed'),
        ('not_required', 'Not Required'),
    ], default='pending', required=True, index=True, tracking=True)
    filed_date = fields.Date(tracking=True)
    arn = fields.Char(string='ARN', tracking=True, help='Acknowledgement Reference Number from the GST portal.')
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True, domain="[('share', '=', False)]")
    is_overdue = fields.Boolean(compute='_compute_late', search='_search_is_overdue')
    days_late = fields.Integer(compute='_compute_late')
    reminder_sent = fields.Boolean(copy=False)
    source_model = fields.Char(readonly=True)
    source_id = fields.Many2oneReference(model_field='source_model', readonly=True,
                                         string='Filed Through')
    note = fields.Text()

    _rn_gst_obligation_uniq = models.Constraint(
        'unique(registration_id, return_type_id, financial_year, return_period)',
        "This return is already in the calendar for this GSTIN and period.",
    )

    @api.depends('registration_id', 'return_type_id', 'return_period', 'financial_year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s %s/%s' % (
                rec.return_type_id.name or '', rec.gstin or '', rec.financial_year or '', rec.return_period or '',
            )

    @api.depends('due_date', 'state', 'filed_date')
    def _compute_late(self):
        today = fields.Date.context_today(self)
        for rec in self:
            end = rec.filed_date if rec.state == 'filed' else today
            late = (end - rec.due_date).days if rec.due_date and end and rec.state != 'not_required' else 0
            rec.days_late = max(late, 0)
            rec.is_overdue = rec.state == 'pending' and late > 0

    def _search_is_overdue(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('state', '=', 'pending') & Domain('due_date', '<', fields.Date.context_today(self))
        return domain if (operator == '=') == value else ~domain

    # ------------------------------------------------------------------
    # Due dates
    # ------------------------------------------------------------------

    def _rn_apply_due_dates(self):
        """Due date from the rule, moved by the most recent matching extension."""
        Extension = self.env['rn.gst.due.extension']
        for rec in self:
            rule_due = rec.rule_id._rn_due_date(rec.period_end)
            extension = Extension.search([
                ('return_type_id', '=', rec.return_type_id.id),
                ('financial_year', '=', rec.financial_year),
                ('return_period', '=', rec.return_period),
            ], order='id desc').filtered(lambda e: e._rn_covers(rec.registration_id))[:1]
            vals = {
                'rule_due_date': rule_due,
                'due_date': extension.new_due_date or rule_due,
                'extension_id': extension.id,
            }
            if any(rec[k] != v for k, v in (('rule_due_date', rule_due), ('due_date', vals['due_date']),
                                            ('extension_id', extension))):
                if rec.due_date and rec.due_date != vals['due_date']:
                    vals['reminder_sent'] = False
                rec.write(vals)

    @api.model
    def _rn_generate(self, registrations, financial_year):
        """Create the year's returns for the registrations. Existing ones are left as they are."""
        rules = self.env['rn.gst.due.rule'].search([('return_type_id.active', '=', True)])
        existing = {
            (o.registration_id.id, o.return_type_id.id, o.return_period)
            for o in self.search([('registration_id', 'in', registrations.ids), ('financial_year', '=', financial_year)])
        }
        vals_list = []
        for registration in registrations:
            for rule in rules.filtered(lambda r: r._rn_applies_to(registration)):
                for code, start, end in rule._rn_periods(financial_year):
                    key = (registration.id, rule.return_type_id.id, code)
                    if key in existing or not rule._rn_in_force(end):
                        continue
                    if registration.effective_to and start > registration.effective_to:
                        continue
                    if registration.effective_from and end < registration.effective_from:
                        continue
                    existing.add(key)
                    vals_list.append({
                        'registration_id': registration.id,
                        'return_type_id': rule.return_type_id.id,
                        'rule_id': rule.id,
                        'financial_year': financial_year,
                        'return_period': code,
                        'period_start': start,
                        'period_end': end,
                        'due_date': rule._rn_due_date(end),
                        'user_id': registration.rn_return_user_id.id or False,
                    })
        obligations = self.create(vals_list)
        obligations._rn_apply_due_dates()
        return obligations

    # ------------------------------------------------------------------
    # Filing status
    # ------------------------------------------------------------------

    def action_mark_filed(self):
        for rec in self:
            if rec.state == 'filed':
                continue
            rec.write({'state': 'filed', 'filed_date': rec.filed_date or fields.Date.context_today(rec)})
            rec.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_mark_not_required(self):
        missing = self.filtered(lambda r: not r.note)
        if missing:
            raise UserError(_('Write in the note why %s is not required.', ', '.join(missing.mapped('display_name'))))
        self.write({'state': 'not_required'})
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_reset_pending(self):
        self.write({'state': 'pending', 'filed_date': False, 'source_model': False, 'source_id': False})
        return True

    def action_open_source(self):
        self.ensure_one()
        if not self.source_model or not self.source_id:
            raise UserError(_('This return is not linked to a filing record.'))
        return {'type': 'ir.actions.act_window', 'res_model': self.source_model, 'res_id': self.source_id,
                'view_mode': 'form'}

    def _rn_sync_filed(self):
        """Mark pending returns filed when the matching Armora filing record is filed."""
        synced = self.browse()
        for rec in self.filtered(lambda r: r.state == 'pending'):
            model, filing_type = FILING_SOURCES.get(rec.return_type_id.code, (None, None))
            if not model or model not in self.env:
                continue
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('gstin', '=', rec.gstin),
                ('financial_year', '=', rec.financial_year),
                ('state', '=', 'filed'),
            ]
            if filing_type:
                domain.append(('filing_type', '=', filing_type))
            if rec.return_period != 'FY':
                domain.append(('return_period', '=', rec.return_period))
            source = self.env[model].sudo().search(domain, limit=1)
            if source:
                rec.write({
                    'state': 'filed',
                    'filed_date': rec.filed_date or fields.Date.context_today(rec),
                    'source_model': model,
                    'source_id': source.id,
                })
                rec.activity_unlink(['mail.mail_activity_data_todo'])
                rec.message_post(body=_(
                    'Marked filed from %(source)s. The filed date is the day this was found (%(date)s); '
                    'change it if the return was filed on another day.',
                    source=source.display_name, date=rec.filed_date,
                ))
                synced |= rec
        return synced

    @api.model
    def _cron_rn_calendar(self):
        pending = self.search([('state', '=', 'pending')])
        pending._rn_sync_filed()
        today = fields.Date.context_today(self)
        for rec in pending.filtered(lambda r: r.state == 'pending' and not r.reminder_sent):
            days = rec.company_id.rn_gst_reminder_days
            user = rec.user_id or rec.registration_id.rn_return_user_id
            if not user or rec.due_date - timedelta(days=days) > today:
                continue
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=rec.due_date,
                summary=_('File %s', rec.display_name),
                user_id=user.id,
            )
            rec.reminder_sent = True
