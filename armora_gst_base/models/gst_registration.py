# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..constants.registration import REGISTRATION_TYPE_SELECTION
from ..exceptions import GstError
from ..services import gstin as gstin_service
from ..services import state_codes as state_code_service


class ArmoraGstRegistration(models.Model):
    """Indian GST registration belonging to a company.

    Supports multi-GSTIN setups. Does not replace ``res.company.vat``; it is
    complementary configuration for the Armora GST suite.
    """

    _name = 'armora.gst.registration'
    _description = 'Armora GST Registration'
    _order = 'company_id, registration_name, id'
    _rec_name = 'registration_name'

    registration_name = fields.Char(
        string='Registration Name',
        required=True,
        index=True,
        help='Internal label for this GST registration (branch, vertical, etc.).',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    gstin = fields.Char(
        string='GSTIN',
        required=True,
        index=True,
        size=15,
        help='15-character GST Identification Number.',
    )
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        required=True,
        index=True,
        domain="[('country_id.code', '=', 'IN')]",
    )
    state_code = fields.Char(
        string='State Code',
        size=2,
        required=True,
        index=True,
        help='Official 2-digit GST TIN / state code.',
    )
    legal_name = fields.Char(
        string='Legal Name',
        help='Legal name as registered under GST, if different from the label.',
    )
    trade_name = fields.Char(
        string='Trade Name',
        help='Trade name as registered under GST, if applicable.',
    )
    registration_type = fields.Selection(
        selection=REGISTRATION_TYPE_SELECTION,
        string='Registration Type',
        required=True,
        default='regular',
        index=True,
    )
    active = fields.Boolean(default=True, index=True)
    effective_from = fields.Date(string='Effective From')
    effective_to = fields.Date(string='Effective To')
    notes = fields.Text(string='Notes')

    _gstin_length_check = models.Constraint(
        'CHECK (char_length(gstin) = 15)',
        "GSTIN must be exactly 15 characters.",
    )

    @api.depends('registration_name', 'gstin', 'company_id', 'company_id.name')
    def _compute_display_name(self):
        multi = self.env.user.has_group('base.group_multi_company')
        for record in self:
            if record.registration_name and record.gstin:
                name = '%s (%s)' % (record.registration_name, record.gstin)
            else:
                name = (
                    record.registration_name
                    or record.gstin
                    or _('GST Registration')
                )
            if multi and record.company_id:
                name = '%s [%s]' % (name, record.company_id.name)
            record.display_name = name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._prepare_gst_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if any(key in vals for key in ('gstin', 'state_id', 'state_code')):
            self._prepare_gst_vals(vals, for_write=True)
        return super().write(vals)

    @api.model
    def _prepare_gst_vals(self, vals, for_write=False):
        """Normalize GSTIN and keep state_code consistent. Never invent missing GSTIN."""
        del for_write  # reserved for future write-specific behavior
        if 'gstin' in vals and vals.get('gstin'):
            vals['gstin'] = gstin_service.normalize_gstin(vals['gstin'])
            try:
                gstin_state = gstin_service.get_gstin_state_code(vals['gstin'])
            except GstError as err:
                raise ValidationError(_('%s') % err) from err
            if not vals.get('state_code'):
                vals['state_code'] = gstin_state
            if not vals.get('state_id'):
                state = self.env['res.country.state'].search([
                    ('country_id.code', '=', 'IN'),
                    ('l10n_in_tin', '=', gstin_state),
                ], limit=1)
                if state:
                    vals['state_id'] = state.id

        if vals.get('state_code'):
            try:
                vals['state_code'] = state_code_service.normalize_state_code(vals['state_code'])
            except GstError as err:
                raise ValidationError(_('%s') % err) from err

        if vals.get('state_id') and not vals.get('state_code'):
            state = self.env['res.country.state'].browse(vals['state_id'])
            if state.l10n_in_tin:
                vals['state_code'] = state_code_service.normalize_state_code(state.l10n_in_tin)

    @api.onchange('gstin')
    def _onchange_gstin(self):
        if not self.gstin:
            return
        normalized = gstin_service.normalize_gstin(self.gstin)
        self.gstin = normalized
        result = gstin_service.validate_gstin(normalized)
        if result['status'] != 'valid':
            return {
                'warning': {
                    'title': _('Invalid GSTIN'),
                    'message': result.get('message') or _('GSTIN is invalid.'),
                }
            }
        state_code = result['state_code']
        self.state_code = state_code
        state = self.env['res.country.state'].search([
            ('country_id.code', '=', 'IN'),
            ('l10n_in_tin', '=', state_code),
        ], limit=1)
        if state:
            self.state_id = state

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id and self.state_id.l10n_in_tin:
            self.state_code = state_code_service.normalize_state_code(self.state_id.l10n_in_tin)

    @api.constrains('gstin')
    def _check_gstin(self):
        for record in self:
            result = gstin_service.validate_gstin(record.gstin)
            if result['status'] != 'valid':
                raise ValidationError(
                    _('GSTIN "%(gstin)s": %(message)s') % {
                        'gstin': record.gstin or '',
                        'message': result.get('message') or _('Invalid GSTIN.'),
                    }
                )
            if result['normalized'] != record.gstin:
                raise ValidationError(
                    _('GSTIN must be normalized (expected %(expected)s).')
                    % {'expected': result['normalized']}
                )

    @api.constrains('gstin', 'state_id', 'state_code')
    def _check_gstin_state_consistency(self):
        for record in self:
            try:
                gstin_state = gstin_service.get_gstin_state_code(record.gstin)
                code = state_code_service.normalize_state_code(record.state_code)
            except GstError as err:
                raise ValidationError(_('%s') % err) from err
            if code != gstin_state:
                raise ValidationError(
                    _('State code %(code)s does not match GSTIN prefix %(gstin_state)s.')
                    % {'code': code, 'gstin_state': gstin_state}
                )
            if record.state_id.l10n_in_tin:
                tin = state_code_service.normalize_state_code(record.state_id.l10n_in_tin)
                if tin != gstin_state:
                    raise ValidationError(
                        _('State %(state)s (TIN %(tin)s) does not match GSTIN prefix %(gstin_state)s.')
                        % {
                            'state': record.state_id.display_name,
                            'tin': tin,
                            'gstin_state': gstin_state,
                        }
                    )

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for record in self:
            if record.effective_from and record.effective_to:
                if record.effective_to < record.effective_from:
                    raise ValidationError(
                        _('Effective To must be on or after Effective From.')
                    )

    @api.constrains('company_id', 'gstin', 'active')
    def _check_unique_active_gstin(self):
        """Prevent two active registrations with the same GSTIN in one company."""
        for record in self.filtered('active'):
            domain = [
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('gstin', '=', record.gstin),
                ('active', '=', True),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _('An active GST registration with GSTIN %(gstin)s already exists '
                      'for company %(company)s.')
                    % {
                        'gstin': record.gstin,
                        'company': record.company_id.display_name,
                    }
                )
