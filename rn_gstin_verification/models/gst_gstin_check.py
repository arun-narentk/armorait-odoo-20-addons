# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

from odoo.addons.rn_gst_base.services import gstin as gstin_service

CHECK_RESULTS = [
    ('format_ok', 'Structure OK'),
    ('format_invalid', 'Structure Invalid'),
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('unavailable', 'Check Unavailable'),
]
# Results that come from the GST portal or a person who looked at it.
AUTHORITY_RESULTS = ('active', 'inactive')


class RnGstGstinCheck(models.Model):
    """One GSTIN check of a partner: how it was done, by whom, and what it showed."""

    _name = 'rn.gst.gstin.check'
    _description = 'GSTIN Check'
    _order = 'check_date desc, id desc'
    _rec_name = 'gstin'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    gstin = fields.Char(string='GSTIN', required=True, index=True)
    check_date = fields.Datetime(required=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Checked By', default=lambda self: self.env.user)
    method = fields.Selection([
        ('structure', 'Structure check'),
        ('portal', 'GST status service'),
        ('manual', 'Manual check on GST portal'),
    ], required=True)
    result = fields.Selection(CHECK_RESULTS, required=True, index=True)
    portal_status = fields.Char(help='Status text as shown by the GST portal, e.g. Active, Cancelled, Suspended.')
    effective_date = fields.Date(help='Date the status took effect, when the portal shows it.')
    legal_name = fields.Char(string='Legal Name on Portal')
    trade_name = fields.Char(string='Trade Name on Portal')
    state_mismatch = fields.Boolean(
        string='State Mismatch',
        help="The GSTIN state code does not match the state on the partner's address.",
    )
    name_mismatch = fields.Boolean(
        string='Name Mismatch',
        help='The legal or trade name seen on the portal does not match the partner name.',
    )
    message = fields.Text()
    attachment_id = fields.Many2one('ir.attachment', string='Proof', ondelete='set null')

    @api.model
    def _rn_structure_vals(self, partner):
        """Values of a structure check of the partner's current GSTIN (no network call)."""
        partner = partner.commercial_partner_id
        check = gstin_service.validate_gstin(partner.vat)
        vals = {
            'partner_id': partner.id,
            'gstin': check['normalized'] or partner.vat or '',
            'method': 'structure',
            'result': 'format_ok' if check['status'] == 'valid' else 'format_invalid',
            'message': check['message'],
        }
        if check.get('state_code') and partner.state_id.country_id.code == 'IN' and partner.state_id.l10n_in_tin:
            vals['state_mismatch'] = partner.state_id.l10n_in_tin.zfill(2) != check['state_code']
            if vals['state_mismatch']:
                vals['message'] += ' ' + _(
                    'State code %(code)s does not match the address state %(state)s (%(tin)s).',
                    code=check['state_code'], state=partner.state_id.name, tin=partner.state_id.l10n_in_tin,
                )
        return vals
