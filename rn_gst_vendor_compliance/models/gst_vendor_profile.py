# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.rn_gst_base.services import gstin as gstin_service

PURCHASE_TYPES = ('in_invoice', 'in_refund')
DECISIONS = [
    ('allow', 'Allow'),
    ('warn', 'Warn'),
    ('approve', 'Needs Approval'),
    ('block', 'Block'),
]
RISKS = [
    ('unknown', 'Unknown'),
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]


class RnGstVendorFinding(models.Model):
    _name = 'rn.gst.vendor.finding'
    _description = 'Supplier GST Finding'
    _order = 'penalty desc, id'

    profile_id = fields.Many2one('rn.gst.vendor.profile', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='profile_id.company_id', store=True)
    code = fields.Char(required=True)
    severity = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')], required=True)
    message = fields.Char(required=True)
    count = fields.Integer()
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='profile_id.company_id.currency_id')
    penalty = fields.Integer(help='Points taken off the score.')


class RnGstVendorProfile(models.Model):
    """GST risk of one supplier for one company, built from data already in Odoo."""

    _name = 'rn.gst.vendor.profile'
    _description = 'Supplier GST Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'score, id'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, index=True, ondelete='cascade',
                                 domain="[('parent_id', '=', False)]")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    gstin = fields.Char(related='partner_id.vat', string='GSTIN')
    gst_treatment = fields.Selection(related='partner_id.l10n_in_gst_treatment')
    gstin_status = fields.Selection([
        ('none', 'No GSTIN'),
        ('foreign', 'Foreign Supplier'),
        ('invalid', 'Structure Invalid'),
        ('structure_ok', 'Structure OK'),
        ('active', 'Active'),
        ('inactive', 'Not Active'),
        ('unknown', 'Not Verified'),
    ], string='GSTIN Status', readonly=True)
    bill_count = fields.Integer(string='Bills (12 months)', readonly=True)
    bill_amount = fields.Monetary(string='Purchases (12 months)', readonly=True, currency_field='currency_id')
    missing_2b_count = fields.Integer(string='Bills Not in GSTR-2B', readonly=True)
    itc_at_risk = fields.Monetary(string='ITC at Risk', readonly=True, currency_field='currency_id',
                                  help='GST on bills not found in GSTR-2B.')
    score = fields.Integer(readonly=True, default=100, tracking=True)
    risk = fields.Selection(RISKS, readonly=True, default='unknown', tracking=True, index=True)
    computed_decision = fields.Selection(DECISIONS, string='Suggested Decision', readonly=True, default='allow')
    decision_override = fields.Selection(DECISIONS, string='Decision Override', tracking=True)
    override_reason = fields.Text(tracking=True)
    decision = fields.Selection(DECISIONS, compute='_compute_decision', store=True, index=True, tracking=True)
    finding_ids = fields.One2many('rn.gst.vendor.finding', 'profile_id', string='Findings')
    refreshed_at = fields.Datetime(readonly=True)

    _rn_gst_vendor_profile_uniq = models.Constraint(
        'unique(company_id, partner_id)', "This supplier already has a GST profile in this company.",
    )

    @api.depends('computed_decision', 'decision_override')
    def _compute_decision(self):
        for profile in self:
            profile.decision = profile.decision_override or profile.computed_decision

    def write(self, vals):
        if vals.get('decision_override') and not vals.get('override_reason') and not all(self.mapped('override_reason')):
            raise UserError(_('Write the reason for overriding the purchase decision.'))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

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
        valid = gstin_service.validate_gstin(partner.vat)['status'] == 'valid'
        return 'structure_ok' if valid else 'invalid'

    def _rn_findings(self):
        """List of finding dicts, from the supplier's bills and the other GST apps."""
        self.ensure_one()
        partner = self.partner_id
        since = fields.Date.context_today(self) - relativedelta(months=12)
        Move = self.env['account.move'].sudo()
        bills = Move.search([
            ('company_id', '=', self.company_id.id),
            ('commercial_partner_id', '=', partner.id),
            ('move_type', 'in', PURCHASE_TYPES),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', since),
        ])
        findings = []
        status = self._rn_gstin_status()
        self.gstin_status = status
        self.bill_count = len(bills.filtered(lambda m: m.move_type == 'in_invoice'))
        self.bill_amount = -sum(bills.mapped('amount_untaxed_signed'))
        treatment = partner.l10n_in_gst_treatment

        if status == 'inactive':
            findings.append(dict(code='gstin_inactive', severity='error', penalty=60,
                                 message=_('GSTIN is not active on the GST portal: no ITC on its bills.')))
        elif status == 'invalid':
            findings.append(dict(code='gstin_invalid', severity='error', penalty=50,
                                 message=_('GSTIN structure or checksum is invalid.')))
        elif status == 'none' and treatment in ('regular', 'composition', 'special_economic_zone'):
            findings.append(dict(code='gstin_missing', severity='error', penalty=30,
                                 message=_('Registered supplier without a GSTIN in Odoo.')))
        elif status in ('structure_ok', 'unknown'):
            findings.append(dict(code='gstin_not_verified', severity='info', penalty=5,
                                 message=_('GSTIN not verified on the GST portal yet.')))

        gst_bills = bills.filtered(
            lambda m: m.move_type == 'in_invoice'
            and m.invoice_line_ids.tax_ids.flatten_taxes_hierarchy().filtered('l10n_in_gst_tax_type')
            and not m.invoice_line_ids.tax_ids.flatten_taxes_hierarchy().filtered('l10n_in_reverse_charge')
        )
        if treatment == 'composition' and gst_bills:
            findings.append(dict(code='composition_tax', severity='error', penalty=20, count=len(gst_bills),
                                 message=_('Composition supplier charged GST on %s bill(s); composition dealers cannot '
                                           'collect tax and no ITC is allowed.', len(gst_bills))))
        if treatment in ('unregistered', 'consumer') and gst_bills:
            findings.append(dict(code='unregistered_tax', severity='error', penalty=20, count=len(gst_bills),
                                 message=_('Unregistered supplier charged GST on %s bill(s).', len(gst_bills))))

        if 'rn_gst_error_count' in Move._fields:
            with_errors = bills.filtered(lambda m: m.rn_gst_error_count)
            if with_errors:
                findings.append(dict(code='bill_errors', severity='warning', count=len(with_errors),
                                     penalty=min(2 * len(with_errors), 10),
                                     message=_('%s bill(s) with GST validation errors.', len(with_errors))))
        if 'rn_gst_tax_mismatch' in Move._fields:
            wrong_tax = bills.filtered('rn_gst_tax_mismatch')
            if wrong_tax:
                findings.append(dict(code='tax_type', severity='warning', count=len(wrong_tax),
                                     penalty=min(3 * len(wrong_tax), 15),
                                     message=_('%s bill(s) with IGST where CGST/SGST is due, or the other way round.',
                                               len(wrong_tax))))
        if 'rn.gst.gstr2b.line' in self.env:
            lines = self.env['rn.gst.gstr2b.line'].sudo().search([
                ('company_id', '=', self.company_id.id),
                ('partner_id', '=', partner.id),
                ('invoice_date', '>=', since),
                ('reconciliation_id.state', '!=', 'cancelled'),
                ('match_state', 'in', ('missing_in_2b', 'mismatch')),
            ])
            missing = lines.filtered(lambda l: l.match_state == 'missing_in_2b')
            mismatch = lines - missing
            at_risk = sum(missing.mapped(lambda l: l.igst_amount + l.cgst_amount + l.sgst_amount + l.cess_amount))
            self.missing_2b_count = len(missing)
            self.itc_at_risk = at_risk
            if missing:
                findings.append(dict(code='not_in_2b', severity='error', count=len(missing), amount=at_risk,
                                     penalty=min(5 * len(missing), 30),
                                     message=_('%s bill(s) not reported by the supplier in GSTR-2B.', len(missing))))
            if mismatch:
                findings.append(dict(code='2b_mismatch', severity='warning', count=len(mismatch),
                                     penalty=min(3 * len(mismatch), 15),
                                     message=_('%s bill(s) differ from GSTR-2B.', len(mismatch))))
        else:
            self.missing_2b_count = 0
            self.itc_at_risk = 0.0
        if 'rn.gst.itc.entry' in self.env:
            reversals = self.env['rn.gst.itc.entry'].sudo().search([
                ('company_id', '=', self.company_id.id),
                ('partner_id', '=', partner.id),
                ('entry_type', '=', 'rule37'),
                ('reversal_date', '>=', since),
            ])
            if reversals:
                findings.append(dict(code='rule37', severity='warning', count=len(reversals),
                                     amount=sum(reversals.mapped('total')), penalty=10,
                                     message=_('%s Rule 37 reversal(s): bills unpaid after 180 days.', len(reversals))))
        return findings

    def action_refresh(self):
        for profile in self:
            findings = profile._rn_findings()
            score = max(100 - sum(f.get('penalty', 0) for f in findings), 0)
            if not profile.bill_count and profile.gstin_status not in ('inactive', 'invalid'):
                risk = 'unknown'
            else:
                risk = 'low' if score >= 80 else 'medium' if score >= 60 else 'high'
            if profile.gstin_status in ('inactive', 'invalid'):
                decision = 'block'
            else:
                decision = {'low': 'allow', 'unknown': 'allow', 'medium': 'warn', 'high': 'approve'}[risk]
            profile.write({
                'finding_ids': [Command.clear()] + [Command.create(f) for f in findings],
                'score': score,
                'risk': risk,
                'computed_decision': decision,
                'refreshed_at': fields.Datetime.now(),
            })
        return True

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bills of %s', self.partner_id.display_name),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('commercial_partner_id', '=', self.partner_id.id), ('move_type', 'in', PURCHASE_TYPES),
                       ('company_id', '=', self.company_id.id)],
            'context': {'create': False},
        }

    @api.model
    def _rn_create_missing(self, companies):
        """Profiles for every supplier with a posted bill in the last 12 months."""
        since = fields.Date.context_today(self) - relativedelta(months=12)
        created = self.browse()
        for company in companies:
            partners = self.env['account.move'].sudo()._read_group([
                ('company_id', '=', company.id), ('move_type', 'in', PURCHASE_TYPES),
                ('state', '=', 'posted'), ('invoice_date', '>=', since),
            ], ['commercial_partner_id'])
            existing = self.search([('company_id', '=', company.id)]).partner_id
            new = [p.id for (p,) in partners if p and p not in existing]
            created |= self.create([{'company_id': company.id, 'partner_id': pid} for pid in new])
        return created

    def action_create_all(self):
        """List button: make profiles for every recent supplier and refresh them."""
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
