# -*- coding: utf-8 -*-
import calendar
from datetime import date

from odoo import _, api, models
from odoo.exceptions import UserError


class RnGstFilingGenerateWizard(models.TransientModel):
    _inherit = 'rn.gst.filing.generate.wizard'

    def action_create_and_load(self):
        self.ensure_one()
        if self.filing_type == 'gstr3b':
            return self._action_open_gstr3b()
        return super().action_create_and_load()

    def _action_open_gstr3b(self):
        self.ensure_one()
        Gstr3b = self.env['rn.gst.3b']
        start, end = self.env['rn.gst.filing'].compute_period_dates(
            self.financial_year, self.return_period, self.filing_frequency
        )
        existing = Gstr3b.search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
        ], limit=1)
        if not existing:
            month = end.month + 1
            year = end.year
            if month > 12:
                month = 1
                year += 1
            due_date = date(year, month, min(20, calendar.monthrange(year, month)[1]))
            gstr1 = self.env['rn.gst.filing'].search([
                ('company_id', '=', self.company_id.id),
                ('gstin', '=', self.gstin),
                ('filing_type', '=', 'gstr1'),
                ('financial_year', '=', self.financial_year),
                ('return_period', '=', self.return_period),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            existing = Gstr3b.create({
                'company_id': self.company_id.id,
                'gstin': self.gstin,
                'financial_year': self.financial_year,
                'return_period': self.return_period,
                'period_start': start,
                'period_end': end,
                'due_date': due_date,
                'net_tax_liability': gstr1.amount_total_tax if gstr1 else 0.0,
                'liability_igst': gstr1.amount_igst if gstr1 else 0.0,
                'liability_cgst': gstr1.amount_cgst if gstr1 else 0.0,
                'liability_sgst': gstr1.amount_sgst if gstr1 else 0.0,
                'liability_cess': gstr1.amount_cess if gstr1 else 0.0,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('GSTR-3B'),
            'res_model': 'rn.gst.3b',
            'view_mode': 'form',
            'res_id': existing.id,
            'target': 'current',
        }
