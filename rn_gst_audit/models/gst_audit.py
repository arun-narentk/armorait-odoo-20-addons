# -*- coding: utf-8 -*-
import io
import json

import xlsxwriter
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

RESULTS = [
    ('pass', 'Pass'),
    ('warning', 'Warning'),
    ('fail', 'Fail'),
    ('unknown', 'Not Checked'),
]
SALE_TYPES = ('out_invoice', 'out_refund', 'out_receipt')
PURCHASE_TYPES = ('in_invoice', 'in_refund', 'in_receipt')


class RnGstAudit(models.Model):
    """A GST review of one period: checks across the Armora GST apps, with sign-off."""

    _name = 'rn.gst.audit'
    _description = 'GST Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    gstin = fields.Char(string='GSTIN', default=lambda self: self.env.company.vat)
    date_from = fields.Date(required=True, tracking=True)
    date_to = fields.Date(required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('signed', 'Signed'),
    ], default='draft', required=True, tracking=True)
    check_ids = fields.One2many('rn.gst.audit.check', 'audit_id', string='Checklist')
    pass_count = fields.Integer(compute='_compute_counts', store=True)
    warning_count = fields.Integer(compute='_compute_counts', store=True)
    fail_count = fields.Integer(compute='_compute_counts', store=True)
    unknown_count = fields.Integer(string='Not Checked', compute='_compute_counts', store=True)
    prepared_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    prepared_on = fields.Datetime(readonly=True)
    reviewed_by_id = fields.Many2one('res.users', readonly=True, tracking=True)
    reviewed_on = fields.Datetime(readonly=True)
    review_note = fields.Text(tracking=True)
    pack_id = fields.Many2one('ir.attachment', string='Audit Pack', readonly=True, copy=False)

    @api.depends('check_ids.result')
    def _compute_counts(self):
        for audit in self:
            results = audit.check_ids.mapped('result')
            audit.pass_count = results.count('pass')
            audit.warning_count = results.count('warning')
            audit.fail_count = results.count('fail')
            audit.unknown_count = results.count('unknown')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for audit in self:
            if audit.date_to < audit.date_from:
                raise UserError(_('The end date must be after the start date.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.audit') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(lambda a: a.state == 'signed') and set(vals) - {
            'state', 'message_follower_ids', 'activity_ids', 'message_ids', 'review_note',
        }:
            raise UserError(_('A signed GST audit is locked. Reopen it first.'))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _rn_months(self):
        self.ensure_one()
        month = self.date_from.replace(day=1)
        months = []
        while month <= self.date_to:
            months.append(month)
            month += relativedelta(months=1)
        return months

    def _rn_move_domain(self, move_types):
        return [
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

    def _rn_count_check(self, code, area, name, model, domain, fail_message, result_if_found='fail'):
        """Check that passes when no record matches ``domain``."""
        if model not in self.env:
            return dict(code=code, area=area, name=name, result='unknown',
                        message=_('The app for this check is not installed.'))
        count = self.env[model].sudo().search_count(domain)
        return dict(
            code=code, area=area, name=name, count=count, model=model, domain=json.dumps(domain, default=str),
            result=result_if_found if count else 'pass',
            message=(fail_message % count) if count else _('No problem found.'),
        )

    def _rn_field_check(self, code, area, name, field, domain, fail_message, result_if_found='fail'):
        """Check on account.move that needs a field of another Armora app."""
        if field not in self.env['account.move']._fields:
            return dict(code=code, area=area, name=name, result='unknown',
                        message=_('The app for this check is not installed.'))
        return self._rn_count_check(code, area, name, 'account.move', domain, fail_message, result_if_found)

    def _rn_checks(self):
        self.ensure_one()
        sales = self._rn_move_domain(SALE_TYPES)
        bills = self._rn_move_domain(PURCHASE_TYPES)
        both = self._rn_move_domain(SALE_TYPES + PURCHASE_TYPES)
        company = self.company_id.id
        checks = [
            self._rn_field_check('validator_errors', 'invoices', _('Invoices and bills without GST errors'),
                                 'rn_gst_error_count', both + [('rn_gst_error_count', '>', 0)],
                                 _('%s document(s) with GST validation errors.')),
            self._rn_field_check('not_validated', 'invoices', _('All invoices validated'),
                                 'rn_gst_validation_status', sales + [('rn_gst_validation_status', '=', 'pending')],
                                 _('%s sales document(s) never run through the GST validator.'), 'warning'),
            self._rn_field_check('blocked', 'invoices', _('No invoice blocked for filing'),
                                 'rn_gst_readiness', both + [('rn_gst_readiness', '=', 'blocked')],
                                 _('%s document(s) blocked for filing and not approved.')),
            self._rn_field_check('tax_type', 'invoices', _('IGST and CGST/SGST used correctly'),
                                 'rn_gst_tax_mismatch', both + [('rn_gst_tax_mismatch', '=', True)],
                                 _('%s document(s) with the wrong kind of GST for the supply.')),
            self._rn_field_check('credit_notes', 'invoices', _('Credit notes follow GST rules'),
                                 'rn_cn_check_state', both + [('rn_cn_check_state', '=', 'error')],
                                 _('%s credit note(s) break a GST rule.')),
            self._rn_field_check('exports', 'invoices', _('Exports and SEZ supplies in order'),
                                 'rn_exp_check_state', sales + [('rn_exp_check_state', '=', 'error')],
                                 _('%s export or SEZ invoice(s) with errors (LUT, Rule 96A, shipping bill).')),
            self._rn_field_check('einvoice', 'documents', _('Every e-invoice has an IRN'),
                                 'rn_einv_state', sales + [('rn_einv_state', 'in', ('pending', 'failed', 'cancel_needed'))],
                                 _('%s invoice(s) without a valid IRN.')),
            self._rn_field_check('ewaybill', 'documents', _('Goods invoices have e-way bills'),
                                 'rn_ewb_missing', both + [('rn_ewb_missing', '=', True)],
                                 _('%s invoice(s) above the limit without an e-way bill.'), 'warning'),
            self._rn_count_check('exceptions', 'follow_up', _('No open GST exception'), 'rn.gst.exception', [
                ('company_id', '=', company), ('state', 'in', ('new', 'in_progress', 'waiting')),
                ('severity', '=', 'error'),
            ], _('%s GST exception(s) with errors still open.'), 'warning'),
            self._rn_count_check('sales_check', 'follow_up', _('Sales check findings closed'), 'rn.gst.sales.recon.line', [
                ('company_id', '=', company), ('state', '=', 'open'), ('severity', '=', 'error'),
                ('recon_id.period_start', '<=', self.date_to), ('recon_id.period_end', '>=', self.date_from),
            ], _('%s sales check error(s) still open.')),
            self._rn_count_check('purchase_check', 'follow_up', _('Purchase check findings closed'),
                                 'rn.gst.purchase.recon.line', [
                ('company_id', '=', company), ('state', '=', 'open'), ('severity', '=', 'error'),
                ('invoice_date', '>=', self.date_from), ('invoice_date', '<=', self.date_to),
            ], _('%s purchase check error(s) still open.')),
        ]
        if 'rn.gst.vendor.profile' in self.env:
            blocked = self.env['rn.gst.vendor.profile'].sudo().search([
                ('company_id', '=', company), ('decision', '=', 'block'),
            ]).partner_id
            checks.append(self._rn_count_check(
                'blocked_suppliers', 'follow_up', _('No bills from blocked suppliers'), 'account.move',
                bills + [('commercial_partner_id', 'in', blocked.ids)],
                _('%s bill(s) from suppliers whose GST decision is Block (check ITC).'),
            ))
        else:
            checks.append(dict(code='blocked_suppliers', area='follow_up', name=_('No bills from blocked suppliers'),
                               result='unknown', message=_('The app for this check is not installed.')))
        checks += self._rn_return_checks()
        return checks

    def _rn_return_checks(self):
        """Returns filed, GSTR-2B reconciled and ITC ledger locked for every month of the period."""
        self.ensure_one()
        company = self.company_id.id
        today = fields.Date.context_today(self)
        checks = []
        if 'rn.gst.obligation' in self.env:
            checks.append(self._rn_count_check('returns_filed', 'returns', _('Returns filed by their due date'),
                                               'rn.gst.obligation', [
                ('company_id', '=', company), ('period_end', '>=', self.date_from),
                ('period_end', '<=', self.date_to), ('state', '=', 'pending'), ('due_date', '<', today),
            ], _('%s return(s) of the period past due and not filed.')))
        else:
            checks.append(dict(code='returns_filed', area='returns', name=_('Returns filed by their due date'),
                               result='unknown', message=_('The app for this check is not installed.')))
        Period = self.env['rn.gst.filing.period']
        periods = [(Period.current_financial_year(m), '%02d' % m.month) for m in self._rn_months()]
        for code, name, model, extra, states, result in (
            ('gstr1_filed', _('GSTR-1 filed for each month'), 'rn.gst.filing', [('filing_type', '=', 'gstr1')],
             ('filed',), 'fail'),
            ('gstr3b_filed', _('GSTR-3B filed for each month'), 'rn.gst.3b', [], ('filed',), 'fail'),
            ('gstr2b_reconciled', _('GSTR-2B reconciled for each month'), 'rn.gst.gstr2b', [],
             ('matched', 'closed'), 'warning'),
            ('itc_locked', _('ITC ledger locked for each month'), 'rn.gst.itc.ledger', [], ('locked',), 'warning'),
        ):
            if model not in self.env:
                checks.append(dict(code=code, area='returns', name=name, result='unknown',
                                   message=_('The app for this check is not installed.')))
                continue
            Model = self.env[model].sudo()
            missing = []
            for financial_year, month in periods:
                domain = [('company_id', '=', company), ('financial_year', '=', financial_year),
                          ('return_period', '=', month), ('state', 'in', states)] + extra
                if self.gstin and 'gstin' in Model._fields:
                    domain.append(('gstin', '=', self.gstin))
                if not Model.search_count(domain):
                    missing.append('%s/%s' % (financial_year, month))
            checks.append(dict(
                code=code, area='returns', name=name, count=len(missing),
                result=result if missing else 'pass',
                message=_('Missing for: %s', ', '.join(missing)) if missing else _('Done for every month.'),
            ))
        return checks

    def action_run(self):
        for audit in self:
            if audit.state == 'signed':
                raise UserError(_('A signed GST audit is locked. Reopen it first.'))
            checks = audit._rn_checks()
            audit.write({
                'check_ids': [Command.clear()] + [Command.create(dict(c, sequence=i)) for i, c in enumerate(checks)],
                'state': 'checked',
                'prepared_by_id': self.env.user.id,
                'prepared_on': fields.Datetime.now(),
                'reviewed_by_id': False,
                'reviewed_on': False,
            })
            audit.message_post(body=_('Checklist run: %(p)s pass, %(w)s warning, %(f)s fail, %(u)s not checked.',
                                      p=audit.pass_count, w=audit.warning_count, f=audit.fail_count,
                                      u=audit.unknown_count))
        return True

    def action_sign(self):
        for audit in self:
            if audit.state != 'checked':
                raise UserError(_('Run the checklist before signing.'))
            if audit.fail_count and not audit.review_note:
                raise UserError(_('Write a review note on the failed checks before signing.'))
            if audit.prepared_by_id == self.env.user and not self.env.su:
                raise UserError(_('The reviewer must be someone other than the person who prepared the audit.'))
            audit.write({'state': 'signed', 'reviewed_by_id': self.env.user.id,
                         'reviewed_on': fields.Datetime.now()})
        return True

    def action_reopen(self):
        self.write({'state': 'checked'})
        return True

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def action_export_pack(self):
        self.ensure_one()
        if not self.check_ids:
            raise UserError(_('Run the checklist first.'))
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        bold = workbook.add_format({'bold': True})
        sheet = workbook.add_worksheet(_('Checklist'))
        sheet.write_row(0, 0, [_('GST Audit'), self.name, self.company_id.name, self.gstin or ''], bold)
        sheet.write_row(1, 0, [_('Period'), str(self.date_from), str(self.date_to)])
        sheet.write_row(2, 0, [_('Prepared by'), self.prepared_by_id.name or '', _('Reviewed by'),
                               self.reviewed_by_id.name or ''])
        sheet.write_row(4, 0, [_('Area'), _('Check'), _('Result'), _('Count'), _('Details')], bold)
        areas = dict(self.check_ids._fields['area']._description_selection(self.env))
        labels = dict(RESULTS)
        for row, check in enumerate(self.check_ids, start=5):
            sheet.write_row(row, 0, [areas.get(check.area, ''), check.name, labels[check.result], check.count,
                                     check.message or ''])
        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 40)
        sheet.set_column(4, 4, 70)
        for check in self.check_ids.filtered(lambda c: c.result in ('fail', 'warning') and c.model == 'account.move'):
            moves = check._rn_records()
            if not moves:
                continue
            detail = workbook.add_worksheet(check.code[:31])
            detail.write_row(0, 0, [check.name], bold)
            detail.write_row(1, 0, [_('Number'), _('Date'), _('Partner'), _('Total')], bold)
            for row, move in enumerate(moves[:2000], start=2):
                detail.write_row(row, 0, [move.name or '', str(move.invoice_date or ''),
                                          move.partner_id.name or '', move.amount_total_signed])
            detail.set_column(0, 2, 24)
        workbook.close()
        name = '%s.xlsx' % self.name.replace('/', '_')
        self.pack_id.sudo().unlink()
        self.pack_id = self.env['ir.attachment'].create({
            'name': name, 'raw': buffer.getvalue(), 'res_model': self._name, 'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        self.message_post(body=_('Audit pack created.'), attachment_ids=self.pack_id.ids)
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%s?download=true' % self.pack_id.id,
                'target': 'self'}

    def action_send_to_exceptions(self):
        self.ensure_one()
        if 'rn.gst.exception' not in self.env:
            raise UserError(_('Install Armora GST Exceptions to use this.'))
        findings = [{
            'fingerprint': 'audit:%s:%s' % (self.id, check.code),
            'company_id': self.company_id.id,
            'gstin': self.gstin or False,
            'title': '%s: %s' % (self.name, check.name),
            'message': check.message,
            'severity': 'error' if check.result == 'fail' else 'warning',
            'category': 'return',
            'res_model': self._name,
            'res_id': self.id,
        } for check in self.check_ids.filtered(lambda c: c.result in ('fail', 'warning'))]
        # Audit users may not have rights on the inbox; the audit only adds and closes its own problems.
        stats = self.env['rn.gst.exception'].sudo()._rn_sync_findings(
            'other', findings, [self.company_id.id], fingerprint_prefix='audit:%s:' % self.id,
        )
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Sent to GST exceptions'), 'type': 'success',
                       'message': _('%(n)s new, %(u)s already open.', n=stats['created'], u=stats['updated'])},
        }


class RnGstAuditCheck(models.Model):
    _name = 'rn.gst.audit.check'
    _description = 'GST Audit Check'
    _order = 'sequence, id'

    audit_id = fields.Many2one('rn.gst.audit', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='audit_id.company_id', store=True)
    sequence = fields.Integer()
    code = fields.Char(required=True)
    area = fields.Selection([
        ('invoices', 'Invoices'),
        ('documents', 'E-Documents'),
        ('returns', 'Returns'),
        ('follow_up', 'Follow-up'),
    ], required=True)
    name = fields.Char(string='Check', required=True)
    result = fields.Selection(RESULTS, required=True)
    count = fields.Integer()
    message = fields.Char(string='Details')
    model = fields.Char()
    domain = fields.Text()
    note = fields.Char()

    def _rn_records(self):
        self.ensure_one()
        if not self.model or not self.domain or self.model not in self.env:
            return self.env['account.move']
        return self.env[self.model].search(json.loads(self.domain))

    def action_open(self):
        self.ensure_one()
        if not self.model or not self.domain:
            raise UserError(_('This check has no document list.'))
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': self.model,
            'view_mode': 'list,form',
            'domain': json.loads(self.domain),
            'context': {'create': False},
        }
