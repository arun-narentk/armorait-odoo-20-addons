# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RnGstFilingGenerateWizard(models.TransientModel):
    _name = 'rn.gst.filing.generate.wizard'
    _description = 'Generate GST Filing Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    gst_registration_id = fields.Many2one(
        'rn.gst.registration',
        string='GST Registration',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
    )
    gstin = fields.Char(required=True)
    financial_year = fields.Char(required=True)
    return_period = fields.Char(required=True)
    filing_type = fields.Selection([
        ('gstr1', 'GSTR-1'),
        ('gstr1a', 'GSTR-1A'),
        ('gstr3b', 'GSTR-3B'),
        ('gstr9', 'GSTR-9'),
    ], required=True, default='gstr1')
    filing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], required=True, default='monthly')

    step = fields.Selection([
        ('period', 'Period'),
        ('loaded', 'Data Loaded'),
        ('validated', 'Validated'),
        ('generated', 'Generated'),
    ], default='period')

    filing_id = fields.Many2one('rn.gst.filing', readonly=True)

    document_count = fields.Integer(readonly=True)
    count_b2b = fields.Integer(readonly=True)
    count_b2cl = fields.Integer(readonly=True)
    count_b2cs = fields.Integer(readonly=True)
    count_export = fields.Integer(readonly=True)
    count_credit_note = fields.Integer(readonly=True)
    count_debit_note = fields.Integer(readonly=True)
    count_nil = fields.Integer(readonly=True)
    count_hsn = fields.Integer(readonly=True)

    validation_error_count = fields.Integer(readonly=True)
    validation_warning_count = fields.Integer(readonly=True)
    validation_status = fields.Char(readonly=True)
    generated_filename = fields.Char(readonly=True)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            if self.gst_registration_id and self.gst_registration_id.company_id != self.company_id:
                self.gst_registration_id = False
            if not self.gst_registration_id:
                self.gstin = self.company_id.vat or ''

    @api.onchange('gst_registration_id')
    def _onchange_gst_registration_id(self):
        if self.gst_registration_id:
            self.company_id = self.gst_registration_id.company_id
            self.gstin = self.gst_registration_id.gstin or ''

    def _sync_stats_from_filing(self):
        self.ensure_one()
        filing = self.filing_id
        self.write({
            'document_count': filing.document_count,
            'count_b2b': filing.count_b2b,
            'count_b2cl': filing.count_b2cl,
            'count_b2cs': filing.count_b2cs,
            'count_export': filing.count_export,
            'count_credit_note': filing.count_credit_note,
            'count_debit_note': filing.count_debit_note,
            'count_nil': filing.count_nil,
            'count_hsn': filing.count_hsn,
            'validation_error_count': filing.validation_error_count,
            'validation_warning_count': filing.validation_warning_count,
            'validation_status': filing.validation_status,
            'generated_filename': filing.generated_filename,
        })

    def action_create_and_load(self):
        self.ensure_one()
        Filing = self.env['rn.gst.filing']
        start, end = Filing.compute_period_dates(
            self.financial_year, self.return_period, self.filing_frequency
        )
        existing = Filing.search([
            ('company_id', '=', self.company_id.id),
            ('gstin', '=', self.gstin),
            ('filing_type', '=', self.filing_type),
            ('financial_year', '=', self.financial_year),
            ('return_period', '=', self.return_period),
        ], limit=1)
        if existing:
            if existing.state in ('submitted', 'filed', 'cancelled'):
                raise UserError(_('A non-modifiable filing already exists for this period.'))
            filing = existing
            if self.gst_registration_id and not filing.gst_registration_id:
                filing.gst_registration_id = self.gst_registration_id
        else:
            filing = Filing.create({
                'company_id': self.company_id.id,
                'gst_registration_id': self.gst_registration_id.id if self.gst_registration_id else False,
                'gstin': self.gstin,
                'financial_year': self.financial_year,
                'return_period': self.return_period,
                'filing_type': self.filing_type,
                'filing_frequency': self.filing_frequency,
                'period_start': start,
                'period_end': end,
                'state_id': (
                    self.gst_registration_id.state_id.id
                    if self.gst_registration_id
                    else self.company_id.state_id.id
                ),
            })
        filing.action_load_data()
        self.filing_id = filing.id
        self.step = 'loaded'
        self._sync_stats_from_filing()
        return self._reopen()

    def action_validate(self):
        self.ensure_one()
        if not self.filing_id:
            raise UserError(_('Create and load data first.'))
        self.filing_id.action_validate()
        self.step = 'validated'
        self._sync_stats_from_filing()
        return self._reopen()

    def action_generate_excel(self):
        self.ensure_one()
        if not self.filing_id:
            raise UserError(_('Create and load data first.'))
        self.filing_id.action_generate_excel()
        self.step = 'generated'
        self._sync_stats_from_filing()
        return self._reopen()

    def action_open_filing(self):
        self.ensure_one()
        if not self.filing_id:
            raise UserError(_('No filing created yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rn.gst.filing',
            'res_id': self.filing_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
