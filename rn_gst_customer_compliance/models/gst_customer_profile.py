# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models

from odoo.addons.rn_gst_base.services import gstin as gstin_service

SALE_TYPES = ('out_invoice', 'out_refund')
RISKS = [
    ('unknown', 'Unknown'),
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]
CREDIT_NOTE_SHARE = 0.20
EINVOICE_PENDING_DAYS = 7


class RnGstCustomerFinding(models.Model):
    _name = 'rn.gst.customer.finding'
    _description = 'Customer GST Finding'
    _order = 'penalty desc, id'

    profile_id = fields.Many2one('rn.gst.customer.profile', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='profile_id.company_id', store=True)
    code = fields.Char(required=True)
    severity = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')], required=True)
    message = fields.Char(required=True)
    count = fields.Integer()
    penalty = fields.Integer(help='Points taken off the score.')


class RnGstCustomerProfile(models.Model):
    """GST set-up and sales-side problems of one customer for one company."""

    _name = 'rn.gst.customer.profile'
    _description = 'Customer GST Profile'
    _inherit = ['mail.thread']
    _order = 'score, id'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True, ondelete='cascade',
                                 domain="[('parent_id', '=', False)]")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    gstin = fields.Char(related='partner_id.vat', string='GSTIN')
    gst_treatment = fields.Selection(related='partner_id.l10n_in_gst_treatment')
    gstin_status = fields.Selection([
        ('none', 'No GSTIN'),
        ('foreign', 'Foreign Customer'),
        ('invalid', 'Structure Invalid'),
        ('structure_ok', 'Structure OK'),
        ('active', 'Active'),
        ('inactive', 'Not Active'),
        ('unknown', 'Not Verified'),
    ], string='GSTIN Status', readonly=True)
    invoice_count = fields.Integer(string='Invoices (12 months)', readonly=True)
    sales_amount = fields.Monetary(string='Sales (12 months)', readonly=True, currency_field='currency_id')
    credit_amount = fields.Monetary(string='Credit Notes (12 months)', readonly=True, currency_field='currency_id')
    score = fields.Integer(readonly=True, default=100, tracking=True)
    risk = fields.Selection(RISKS, readonly=True, default='unknown', tracking=True, index=True)
    finding_ids = fields.One2many('rn.gst.customer.finding', 'profile_id', string='Findings')
    refreshed_at = fields.Datetime(readonly=True)

    _rn_gst_customer_profile_uniq = models.Constraint(
        'unique(company_id, partner_id)', "This customer already has a GST profile in this company.",
    )

    def _rn_gstin_status(self):
        partner = self.partner_id
        if (partner.country_id and partner.country_id.code != 'IN') or partner.l10n_in_gst_treatment == 'overseas':
            return 'foreign'
        if not partner.vat:
            return 'none'
        if 'rn_gstin_status' in partner._fields and partner.rn_gstin_status not in (False, 'no_gstin', 'not_checked'):
            return {
                'format_invalid': 'invalid', 'format_ok': 'structure_ok', 'active': 'active',
                'inactive': 'inactive', 'unavailable': 'unknown',
            }.get(partner.rn_gstin_status, 'unknown')
        return 'structure_ok' if gstin_service.validate_gstin(partner.vat)['status'] == 'valid' else 'invalid'

    def _rn_findings(self):
        self.ensure_one()
        partner = self.partner_id
        today = fields.Date.context_today(self)
        since = today - relativedelta(months=12)
        Move = self.env['account.move'].sudo()
        moves = Move.search([
            ('company_id', '=', self.company_id.id),
            ('commercial_partner_id', '=', partner.id),
            ('move_type', 'in', SALE_TYPES),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', since),
        ])
        invoices = moves.filtered(lambda m: m.move_type == 'out_invoice')
        refunds = moves - invoices
        status = self._rn_gstin_status()
        self.gstin_status = status
        self.invoice_count = len(invoices)
        self.sales_amount = sum(invoices.mapped('amount_untaxed_signed'))
        self.credit_amount = -sum(refunds.mapped('amount_untaxed_signed'))
        treatment = partner.l10n_in_gst_treatment
        findings = []

        if status == 'inactive':
            findings.append(dict(code='gstin_inactive', severity='error', penalty=40,
                                 message=_('GSTIN is not active on the GST portal: B2B invoices to it are not valid.')))
        elif status == 'invalid':
            findings.append(dict(code='gstin_invalid', severity='error', penalty=40,
                                 message=_('GSTIN structure or checksum is invalid: GSTR-1 will reject its invoices.')))
        if status in ('structure_ok', 'active', 'unknown') and treatment in ('unregistered', 'consumer'):
            findings.append(dict(code='b2b_as_b2c', severity='error', penalty=30, count=len(invoices),
                                 message=_('Customer has a GSTIN but is set up as %s: its invoices go to GSTR-1 as B2C '
                                           'and it cannot take ITC.',
                                           dict(partner._fields['l10n_in_gst_treatment']._description_selection(
                                               self.env)).get(treatment))))
        if status == 'none' and treatment in ('regular', 'composition', 'special_economic_zone', 'deemed_export'):
            findings.append(dict(code='gstin_missing', severity='error', penalty=30,
                                 message=_('Customer is set up as registered but has no GSTIN.')))
        if status in ('structure_ok', 'active', 'unknown', 'invalid') and partner.vat and partner.vat[:2].isdigit():
            tin = partner.state_id.l10n_in_tin if partner.state_id.country_id.code == 'IN' else False
            if tin and tin.zfill(2) != partner.vat[:2]:
                findings.append(dict(code='state_mismatch', severity='warning', penalty=10,
                                     message=_('GSTIN state code %(code)s does not match the address state %(state)s; '
                                               'place of supply may be wrong.', code=partner.vat[:2],
                                               state=partner.state_id.name)))
        if status in ('structure_ok', 'unknown'):
            findings.append(dict(code='gstin_not_verified', severity='info', penalty=5,
                                 message=_('GSTIN not verified on the GST portal yet.')))

        if 'rn_gst_error_count' in Move._fields:
            with_errors = moves.filtered('rn_gst_error_count')
            if with_errors:
                findings.append(dict(code='invoice_errors', severity='warning', count=len(with_errors),
                                     penalty=min(2 * len(with_errors), 10),
                                     message=_('%s invoice(s) with GST validation errors.', len(with_errors))))
        if 'rn_gst_tax_mismatch' in Move._fields:
            wrong_tax = moves.filtered('rn_gst_tax_mismatch')
            if wrong_tax:
                findings.append(dict(code='tax_type', severity='warning', count=len(wrong_tax),
                                     penalty=min(3 * len(wrong_tax), 15),
                                     message=_('%s invoice(s) with IGST where CGST/SGST is due, or the other way round.',
                                               len(wrong_tax))))
        if 'rn_cn_check_state' in Move._fields:
            bad_notes = refunds.filtered(lambda m: m.rn_cn_check_state == 'error')
            if bad_notes:
                findings.append(dict(code='credit_note_errors', severity='warning', count=len(bad_notes),
                                     penalty=min(5 * len(bad_notes), 15),
                                     message=_('%s credit note(s) break a GST rule.', len(bad_notes))))
        if self.sales_amount and self.credit_amount > CREDIT_NOTE_SHARE * self.sales_amount:
            findings.append(dict(code='credit_note_share', severity='warning', penalty=5, count=len(refunds),
                                 message=_('Credit notes are %(share)s%% of sales in the last 12 months.',
                                           share=round(100 * self.credit_amount / self.sales_amount))))
        if 'rn_einv_state' in Move._fields:
            stuck = moves.filtered(
                lambda m: m.rn_einv_state == 'failed'
                or (m.rn_einv_state == 'pending' and m.invoice_date and m.invoice_date < today - timedelta(days=EINVOICE_PENDING_DAYS))
            )
            if stuck:
                findings.append(dict(code='einvoice', severity='warning', count=len(stuck),
                                     penalty=min(3 * len(stuck), 15),
                                     message=_('%s invoice(s) without IRN: e-invoice failed or pending over 7 days.',
                                               len(stuck))))
        return findings

    def action_refresh(self):
        for profile in self:
            findings = profile._rn_findings()
            score = max(100 - sum(f.get('penalty', 0) for f in findings), 0)
            if not profile.invoice_count and not any(f['severity'] == 'error' for f in findings):
                risk = 'unknown'
            else:
                risk = 'low' if score >= 80 else 'medium' if score >= 60 else 'high'
            profile.write({
                'finding_ids': [Command.clear()] + [Command.create(f) for f in findings],
                'score': score,
                'risk': risk,
                'refreshed_at': fields.Datetime.now(),
            })
        return True

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices of %s', self.partner_id.display_name),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('commercial_partner_id', '=', self.partner_id.id), ('move_type', 'in', SALE_TYPES),
                       ('company_id', '=', self.company_id.id)],
            'context': {'create': False},
        }

    @api.model
    def _rn_create_missing(self, companies):
        since = fields.Date.context_today(self) - relativedelta(months=12)
        created = self.browse()
        for company in companies:
            groups = self.env['account.move'].sudo()._read_group([
                ('company_id', '=', company.id), ('move_type', 'in', SALE_TYPES),
                ('state', '=', 'posted'), ('invoice_date', '>=', since),
            ], ['commercial_partner_id'])
            existing = self.search([('company_id', '=', company.id)]).partner_id
            new = [p.id for (p,) in groups if p and p not in existing]
            created |= self.create([{'company_id': company.id, 'partner_id': pid} for pid in new])
        return created

    def action_create_all(self):
        self._rn_create_missing(self.env.companies)
        self.search([('company_id', 'in', self.env.companies.ids)]).action_refresh()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    @api.model
    def _cron_refresh_all(self):
        self._rn_create_missing(self.env['res.company'].search([]))
        self.search([]).action_refresh()

    @api.model
    def _rn_profile_for(self, partner, company):
        return self.search([('partner_id', '=', partner.commercial_partner_id.id), ('company_id', '=', company.id)],
                           limit=1)
