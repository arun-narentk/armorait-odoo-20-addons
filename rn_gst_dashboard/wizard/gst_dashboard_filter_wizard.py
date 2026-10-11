# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstDashboardFilterWizard(models.TransientModel):
    """Apply dashboard filter values onto a dashboard context record."""

    _name = 'rn.gst.dashboard.filter.wizard'
    _description = 'GST Dashboard Filter Wizard'

    dashboard_id = fields.Many2one('rn.gst.dashboard', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True)
    gst_registration_id = fields.Many2one(
        'rn.gst.registration',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
    )
    gstin = fields.Char()
    financial_year = fields.Char()
    return_period = fields.Char()
    date_from = fields.Date()
    date_to = fields.Date()

    def action_apply(self):
        self.ensure_one()
        vals = {
            'company_id': self.company_id.id,
            'gst_registration_id': self.gst_registration_id.id,
            'gstin': self.gstin,
            'financial_year': self.financial_year,
            'return_period': self.return_period,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        self.dashboard_id.write(vals)
        return self.dashboard_id.action_refresh()
