# -*- coding: utf-8 -*-
import calendar
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ArmoraGstFiling(models.Model):
    _inherit = 'armora.gst.filing'

    gstr3b_id = fields.Many2one(
        'armora.gst.3b',
        compute='_compute_gstr3b_link',
        string='GSTR-3B',
    )
    gstr3b_count = fields.Integer(compute='_compute_gstr3b_link')

    @api.depends('company_id', 'gstin', 'financial_year', 'return_period')
    def _compute_gstr3b_link(self):
        Gstr3b = self.env['armora.gst.3b']
        for rec in self:
            gstr3b = Gstr3b.search([
                ('company_id', '=', rec.company_id.id),
                ('gstin', '=', rec.gstin),
                ('financial_year', '=', rec.financial_year),
                ('return_period', '=', rec.return_period),
            ], limit=1)
            rec.gstr3b_id = gstr3b
            rec.gstr3b_count = 1 if gstr3b else 0

    def _gstr3b_due_date(self):
        self.ensure_one()
        if not self.period_end:
            return fields.Date.today()
        month = self.period_end.month + 1
        year = self.period_end.year
        if month > 12:
            month = 1
            year += 1
        return date(year, month, min(20, calendar.monthrange(year, month)[1]))

    def action_open_gstr3b(self):
        self.ensure_one()
        if self.gstr3b_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('GSTR-3B'),
                'res_model': 'armora.gst.3b',
                'view_mode': 'form',
                'res_id': self.gstr3b_id.id,
            }
        return self.action_create_gstr3b()

    def action_create_gstr3b(self):
        self.ensure_one()
        if self.filing_type != 'gstr1':
            raise UserError(_('GSTR-3B is linked from GSTR-1 filings in the same return period.'))
        Gstr3b = self.env['armora.gst.3b']
        existing = Gstr3b.search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
        ], limit=1)
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': _('GSTR-3B'),
                'res_model': 'armora.gst.3b',
                'view_mode': 'form',
                'res_id': existing.id,
            }
        gstr3b = Gstr3b.create({
            'company_id': self.company_id.id,
            'gstin': self.gstin,
            'financial_year': self.financial_year,
            'return_period': self.return_period,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'due_date': self._gstr3b_due_date(),
            'net_tax_liability': self.amount_total_tax,
            'liability_igst': self.amount_igst,
            'liability_cgst': self.amount_cgst,
            'liability_sgst': self.amount_sgst,
            'liability_cess': self.amount_cess,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('GSTR-3B'),
            'res_model': 'armora.gst.3b',
            'view_mode': 'form',
            'res_id': gstr3b.id,
        }
