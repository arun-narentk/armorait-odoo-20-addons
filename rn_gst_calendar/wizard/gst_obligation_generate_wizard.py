# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class RnGstObligationGenerateWizard(models.TransientModel):
    _name = 'rn.gst.obligation.generate.wizard'
    _description = 'Generate GST Returns Due'

    financial_year = fields.Char(
        required=True,
        default=lambda self: self.env['rn.gst.filing.period'].current_financial_year(),
        help='e.g. 2025-26',
    )
    registration_ids = fields.Many2many(
        'rn.gst.registration', string='GSTINs',
        default=lambda self: self.env['rn.gst.registration'].search([('company_id', 'in', self.env.companies.ids)]),
    )

    def action_generate(self):
        self.ensure_one()
        if not self.registration_ids:
            raise UserError(_('Pick at least one GSTIN. Add them under GST Registrations first.'))
        self.env['rn.gst.filing.period'].fy_start_year(self.financial_year)
        created = self.env['rn.gst.obligation']._rn_generate(self.registration_ids, self.financial_year)
        created._rn_sync_filed()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GST Returns %s', self.financial_year),
            'res_model': 'rn.gst.obligation',
            'view_mode': 'list,calendar,kanban,form',
            'domain': [('financial_year', '=', self.financial_year),
                       ('registration_id', 'in', self.registration_ids.ids)],
        }
