# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from odoo.addons.rn_gst_base.services import gstin as gstin_service

from .gst_gstin_check import AUTHORITY_RESULTS, CHECK_RESULTS


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rn_gstin_check_ids = fields.One2many('rn.gst.gstin.check', 'partner_id', string='GSTIN Checks')
    rn_gstin_check_count = fields.Integer(compute='_compute_rn_gstin_check_count')
    rn_gstin_status = fields.Selection(
        [('no_gstin', 'No GSTIN'), ('not_checked', 'Not Checked')] + CHECK_RESULTS,
        string='GSTIN Check Status',
        compute='_compute_rn_gstin_status',
        store=True,
        index=True,
        help='Result of the checks of the current GSTIN. A valid structure is not a government verification.',
    )
    rn_gstin_checked_on = fields.Datetime(string='GSTIN Last Checked', compute='_compute_rn_gstin_status', store=True)
    rn_gstin_verified_on = fields.Datetime(
        string='GSTIN Last Verified',
        compute='_compute_rn_gstin_status',
        store=True,
        help='Last check by the GST status service or by hand on the GST portal.',
    )
    rn_gstin_recheck_due = fields.Boolean(
        string='GSTIN Re-check Due',
        compute='_compute_rn_gstin_recheck_due',
        search='_search_rn_gstin_recheck_due',
    )

    def _compute_rn_gstin_check_count(self):
        counts = dict(self.env['rn.gst.gstin.check']._read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['__count'],
        ))
        for partner in self:
            partner.rn_gstin_check_count = counts.get(partner, 0)

    def _rn_gstin_applies(self):
        """The tax ID is a GSTIN: an Indian partner, or one without country whose tax ID starts with a state code."""
        self.ensure_one()
        if not self.vat:
            return False
        if self.country_id:
            return self.country_id.code == 'IN'
        return self.vat.strip()[:2].isdigit()

    @api.depends('vat', 'country_id', 'rn_gstin_check_ids.result', 'rn_gstin_check_ids.gstin', 'rn_gstin_check_ids.check_date')
    def _compute_rn_gstin_status(self):
        for partner in self:
            gstin = gstin_service.normalize_gstin(partner.vat) if partner._rn_gstin_applies() else ''
            checks = partner.rn_gstin_check_ids.filtered(lambda c: c.gstin == gstin).sorted('check_date', reverse=True)
            authority = checks.filtered(lambda c: c.result in AUTHORITY_RESULTS)[:1]
            structure = checks.filtered(lambda c: c.method == 'structure')[:1]
            unavailable = checks.filtered(lambda c: c.result == 'unavailable')[:1]
            partner.rn_gstin_checked_on = checks[:1].check_date
            partner.rn_gstin_verified_on = authority.check_date
            if not gstin:
                partner.rn_gstin_status = 'no_gstin'
            elif structure.result == 'format_invalid':
                partner.rn_gstin_status = 'format_invalid'
            elif authority:
                partner.rn_gstin_status = authority.result
            elif unavailable:
                partner.rn_gstin_status = 'unavailable'
            elif structure:
                partner.rn_gstin_status = structure.result
            else:
                partner.rn_gstin_status = 'not_checked'

    def _rn_gstin_recheck_limit(self):
        return fields.Datetime.now() - timedelta(days=self.env.company.rn_gstin_recheck_days or 180)

    @api.depends('rn_gstin_verified_on', 'rn_gstin_status')
    def _compute_rn_gstin_recheck_due(self):
        limit = self._rn_gstin_recheck_limit()
        for partner in self:
            partner.rn_gstin_recheck_due = partner.rn_gstin_status not in ('no_gstin', 'format_invalid') and (
                not partner.rn_gstin_verified_on or partner.rn_gstin_verified_on < limit
            )

    def _search_rn_gstin_recheck_due(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('rn_gstin_status', 'not in', ('no_gstin', 'format_invalid')) & (
            Domain('rn_gstin_verified_on', '=', False)
            | Domain('rn_gstin_verified_on', '<', self._rn_gstin_recheck_limit())
        )
        return domain if (operator == '=') == value else ~domain

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def action_rn_gstin_check(self):
        """Structure check, then the GST status service when Indian Accounting has it switched on."""
        Check = self.env['rn.gst.gstin.check']
        partners = self.commercial_partner_id.filtered(lambda p: p._rn_gstin_applies())
        if not partners:
            raise UserError(_('Set the GSTIN of an Indian partner first. Tax IDs of foreign partners are not GSTINs.'))
        company = self.env.company
        use_service = company.l10n_in_gstin_status_feature and company.account_fiscal_country_id.code == 'IN'
        results = []
        for partner in partners:
            structure = Check.create(Check._rn_structure_vals(partner))
            results.append(structure)
            if structure.result == 'format_ok' and use_service:
                results.append(partner._rn_gstin_service_check(structure.gstin))
        return self._rn_gstin_notify(results)

    def _rn_gstin_service_check(self, gstin):
        """Ask Odoo's GSTIN status service (IAP) and keep what it says. Anything other than a
        clear answer is saved as 'Check Unavailable', never as Active."""
        self.ensure_one()
        before = (self.l10n_in_gstin_verified_status, self.l10n_in_gstin_verified_date)
        partner = self.with_context(tracking_disable=True)
        partner.l10n_in_gstin_verified_date = False
        vals = {'partner_id': self.id, 'gstin': gstin, 'method': 'portal'}
        try:
            self.action_l10n_in_verify_gstin_status()
        except (UserError, ValidationError) as err:
            vals.update(result='unavailable', message=str(err))
        else:
            if self.l10n_in_gstin_verified_date:
                active = self.l10n_in_gstin_verified_status
                vals.update(result='active' if active else 'inactive', portal_status=_('Active') if active else _('Not active'))
                if not self.env.company.l10n_in_edi_production_env:
                    vals['message'] = _('Test environment: the GST status service returns a dummy result.')
            else:
                vals.update(result='unavailable', message=_('No answer from the GST status service. Check the IAP credits.'))
        if vals['result'] == 'unavailable':
            partner.write({'l10n_in_gstin_verified_status': before[0], 'l10n_in_gstin_verified_date': before[1]})
        return self.env['rn.gst.gstin.check'].create(vals)

    def _rn_gstin_notify(self, checks):
        labels = dict(CHECK_RESULTS)
        lines = ['%s: %s' % (check.partner_id.display_name, labels[check.result]) for check in checks[-10:]]
        bad = any(check.result in ('format_invalid', 'inactive', 'unavailable') for check in checks)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('GSTIN checked'),
                'message': '\n'.join(lines),
                'type': 'warning' if bad else 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_rn_gstin_manual_check(self):
        self.ensure_one()
        partner = self.commercial_partner_id
        if not partner._rn_gstin_applies():
            raise UserError(_('Set the GSTIN of an Indian partner first. Tax IDs of foreign partners are not GSTINs.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record GST Portal Check'),
            'res_model': 'rn.gst.gstin.manual.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': partner.id},
        }

    def action_rn_gstin_view_checks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GSTIN Checks'),
            'res_model': 'rn.gst.gstin.check',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.commercial_partner_id.id)],
            'context': {'create': False},
        }

    @api.model
    def _rn_gstin_names_match(self, name, other):
        def clean(text):
            text = re.sub(r'[^a-z0-9 ]', ' ', (text or '').lower())
            text = re.sub(r'\b(m s|ms|pvt|private|ltd|limited|llp|the)\b', ' ', text)
            return ' '.join(text.split())
        return bool(clean(name)) and clean(name) == clean(other)

    @api.model
    def _cron_rn_gstin_structure_check(self, limit=2000):
        """Structure-check partners whose current GSTIN has never been checked. Free, no network."""
        Check = self.env['rn.gst.gstin.check']
        partners = self.search([('rn_gstin_status', '=', 'not_checked'), ('is_company', '=', True)], limit=limit)
        partners |= self.search([
            ('rn_gstin_status', '=', 'not_checked'), ('parent_id', '=', False), ('id', 'not in', partners.ids),
        ], limit=max(limit - len(partners), 0))
        for partner in partners:
            company = partner.company_id or self.env.company
            Check.with_company(company).create(dict(Check._rn_structure_vals(partner), company_id=company.id))
