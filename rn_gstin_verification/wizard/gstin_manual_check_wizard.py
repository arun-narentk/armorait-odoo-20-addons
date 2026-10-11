# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class RnGstGstinManualCheckWizard(models.TransientModel):
    """Record what a person saw when looking up a GSTIN on the GST portal."""

    _name = 'rn.gst.gstin.manual.check.wizard'
    _description = 'Record GST Portal Check'

    partner_id = fields.Many2one('res.partner', required=True, readonly=True)
    gstin = fields.Char(related='partner_id.vat', string='GSTIN')
    result = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Not active (cancelled or suspended)'),
    ], required=True, default='active')
    portal_status = fields.Char(string='Status on Portal', help='As shown on the portal, e.g. Active, Cancelled, Suspended.')
    effective_date = fields.Date(string='Status Since')
    legal_name = fields.Char(string='Legal Name on Portal')
    trade_name = fields.Char(string='Trade Name on Portal')
    proof = fields.Binary(string='Screenshot or PDF')
    proof_name = fields.Char()
    note = fields.Text()

    @api.onchange('result')
    def _onchange_result(self):
        if not self.portal_status:
            self.portal_status = _('Active') if self.result == 'active' else False

    def action_save(self):
        self.ensure_one()
        partner = self.partner_id
        Partner = self.env['res.partner']
        names = [n for n in (self.legal_name, self.trade_name) if n]
        name_mismatch = bool(names) and not any(Partner._rn_gstin_names_match(n, partner.name) for n in names)
        check = self.env['rn.gst.gstin.check'].create({
            'partner_id': partner.id,
            'gstin': partner.vat,
            'method': 'manual',
            'result': self.result,
            'portal_status': self.portal_status,
            'effective_date': self.effective_date,
            'legal_name': self.legal_name,
            'trade_name': self.trade_name,
            'name_mismatch': name_mismatch,
            'message': self.note,
        })
        if self.proof:
            check.attachment_id = self.env['ir.attachment'].create({
                'name': self.proof_name or self.proof.filename or 'gstin_check_%s' % partner.vat,
                'raw': self.proof.content,
                'res_model': 'rn.gst.gstin.check',
                'res_id': check.id,
            })
        if name_mismatch:
            partner.message_post(body=_(
                'GSTIN %(gstin)s: name on the GST portal (%(portal)s) does not match the partner name.',
                gstin=partner.vat, portal=' / '.join(names),
            ))
        return {'type': 'ir.actions.act_window_close'}
