# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services import gst_dashboard_service as svc


class ArmoraGstDashboard(models.Model):
    """GST dashboard workspace: filters + aggregated KPIs from suite modules.

    KPI numeric fields are stored and refreshed via services (not recomputed
    GST business rules). Optional-module sections stay at zero / flagged when
    the owning module is not installed.
    """

    _name = 'armora.gst.dashboard'
    _description = 'GST Compliance Dashboard'
    _order = 'last_refresh desc, id desc'

    name = fields.Char(required=True, copy=False, default='New', index=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    gst_registration_id = fields.Many2one(
        'armora.gst.registration',
        string='GST Registration',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        index=True,
    )
    gstin = fields.Char(index=True)
    financial_year = fields.Char(
        help='Financial year label, e.g. 2025-26.',
    )
    return_period = fields.Char(
        help='Monthly period MM within the financial year (e.g. 04 for April).',
    )
    date_from = fields.Date()
    date_to = fields.Date()
    last_refresh = fields.Datetime(copy=False)
    refreshed_by = fields.Many2one('res.users', copy=False)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    # Module availability (live flags)
    module_filing_available = fields.Boolean(compute='_compute_module_flags')
    module_2b_available = fields.Boolean(compute='_compute_module_flags')
    module_validator_available = fields.Boolean(compute='_compute_module_flags')
    module_itc_available = fields.Boolean(compute='_compute_module_flags')
    module_einvoice_available = fields.Boolean(compute='_compute_module_flags')
    module_ewaybill_available = fields.Boolean(compute='_compute_module_flags')
    module_exception_available = fields.Boolean(compute='_compute_module_flags')

    # DOCUMENTS
    total_invoices = fields.Integer(readonly=True, copy=False)
    total_vendor_bills = fields.Integer(readonly=True, copy=False)
    total_credit_notes = fields.Integer(readonly=True, copy=False)
    total_debit_notes = fields.Integer(readonly=True, copy=False)

    # TAX
    taxable_value = fields.Monetary(
        currency_field='currency_id', readonly=True, copy=False,
    )
    amount_cgst = fields.Monetary(
        string='CGST', currency_field='currency_id', readonly=True, copy=False,
    )
    amount_sgst = fields.Monetary(
        string='SGST', currency_field='currency_id', readonly=True, copy=False,
    )
    amount_igst = fields.Monetary(
        string='IGST', currency_field='currency_id', readonly=True, copy=False,
    )
    amount_cess = fields.Monetary(
        string='Cess', currency_field='currency_id', readonly=True, copy=False,
    )
    amount_total_tax = fields.Monetary(
        string='Total Tax', currency_field='currency_id', readonly=True, copy=False,
    )
    tax_data_source = fields.Char(readonly=True, copy=False)

    # FILING
    filing_count = fields.Integer(readonly=True, copy=False)
    pending_filings = fields.Integer(readonly=True, copy=False)
    validated_filings = fields.Integer(readonly=True, copy=False)
    generated_filings = fields.Integer(readonly=True, copy=False)
    submitted_filings = fields.Integer(readonly=True, copy=False)
    filed_filings = fields.Integer(readonly=True, copy=False)
    filing_errors = fields.Integer(readonly=True, copy=False)

    # 2B
    total_2b_records = fields.Integer(readonly=True, copy=False)
    exact_matches = fields.Integer(readonly=True, copy=False)
    partial_matches = fields.Integer(readonly=True, copy=False)
    mismatches = fields.Integer(readonly=True, copy=False)
    missing_in_books = fields.Integer(readonly=True, copy=False)
    missing_in_2b = fields.Integer(readonly=True, copy=False)
    manual_review = fields.Integer(readonly=True, copy=False)

    # VALIDATION
    validated_documents = fields.Integer(readonly=True, copy=False)
    validation_errors = fields.Integer(readonly=True, copy=False)
    validation_warnings = fields.Integer(readonly=True, copy=False)
    blocking_errors = fields.Integer(readonly=True, copy=False)
    unvalidated_documents = fields.Integer(readonly=True, copy=False)

    # EXCEPTIONS
    open_exceptions = fields.Integer(readonly=True, copy=False)
    critical_exceptions = fields.Integer(readonly=True, copy=False)
    high_exceptions = fields.Integer(readonly=True, copy=False)
    resolved_exceptions = fields.Integer(readonly=True, copy=False)

    # ITC (only when armora_gst_itc exposes values)
    eligible_itc = fields.Monetary(
        currency_field='currency_id', readonly=True, copy=False,
    )
    reconciled_itc = fields.Monetary(
        currency_field='currency_id', readonly=True, copy=False,
    )
    unreconciled_itc = fields.Monetary(
        currency_field='currency_id', readonly=True, copy=False,
    )

    # E-INVOICE
    einvoice_total = fields.Integer(readonly=True, copy=False)
    einvoice_generated = fields.Integer(readonly=True, copy=False)
    einvoice_cancelled = fields.Integer(readonly=True, copy=False)
    einvoice_failed = fields.Integer(readonly=True, copy=False)
    einvoice_pending = fields.Integer(readonly=True, copy=False)

    # E-WAY BILL
    ewaybill_total = fields.Integer(readonly=True, copy=False)
    ewaybill_generated = fields.Integer(readonly=True, copy=False)
    ewaybill_active = fields.Integer(readonly=True, copy=False)
    ewaybill_expired = fields.Integer(readonly=True, copy=False)
    ewaybill_cancelled = fields.Integer(readonly=True, copy=False)
    ewaybill_pending = fields.Integer(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'armora.gst.dashboard'
                ) or 'New'
        records = super().create(vals_list)
        records._refresh_kpis()
        return records

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        period = self.env['armora.gst.period']
        if 'financial_year' in fields_list:
            res.setdefault('financial_year', period.current_financial_year(today))
        if 'return_period' in fields_list:
            res.setdefault('return_period', '%02d' % today.month)
        if 'company_id' in fields_list:
            res.setdefault('company_id', self.env.company.id)
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.gst_registration_id and self.gst_registration_id.company_id != self.company_id:
            self.gst_registration_id = False
            self.gstin = False

    @api.onchange('gst_registration_id')
    def _onchange_gst_registration_id(self):
        if self.gst_registration_id:
            self.gstin = self.gst_registration_id.gstin
            self.company_id = self.gst_registration_id.company_id
        elif self.company_id and not self.gstin:
            self.gstin = (self.company_id.vat or '').upper().strip() or False

    @api.onchange('financial_year', 'return_period')
    def _onchange_period(self):
        self.date_from = False
        self.date_to = False
        if not self.financial_year or not self.return_period:
            return
        try:
            start, end = self.env['armora.gst.period'].compute_period_dates(
                self.financial_year,
                self.return_period,
                'monthly',
            )
        except ValidationError:
            return
        self.date_from = start
        self.date_to = end

    @api.constrains('gst_registration_id', 'company_id')
    def _check_registration_company(self):
        for rec in self:
            if (
                rec.gst_registration_id
                and rec.gst_registration_id.company_id != rec.company_id
            ):
                raise ValidationError(
                    _('GST registration must belong to the selected company.')
                )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_('Date From must be on or before Date To.'))

    @api.depends()
    def _compute_module_flags(self):
        availability = svc.module_availability(self.env)
        for rec in self:
            rec.module_filing_available = availability.get('filing', False)
            rec.module_2b_available = availability.get('reconciliation_2b', False)
            rec.module_validator_available = availability.get('invoice_validation', False)
            rec.module_itc_available = availability.get('itc', False)
            rec.module_einvoice_available = availability.get('einvoice', False)
            rec.module_ewaybill_available = availability.get('ewaybill', False)
            rec.module_exception_available = availability.get('exceptions', False)

    def _filters_dict(self):
        self.ensure_one()
        return {
            'company_id': self.company_id.id,
            'gst_registration_id': self.gst_registration_id.id,
            'gstin': self.gstin,
            'financial_year': self.financial_year,
            'return_period': self.return_period,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def _zero_kpi_vals(self):
        return {
            'total_invoices': 0,
            'total_vendor_bills': 0,
            'total_credit_notes': 0,
            'total_debit_notes': 0,
            'taxable_value': 0.0,
            'amount_cgst': 0.0,
            'amount_sgst': 0.0,
            'amount_igst': 0.0,
            'amount_cess': 0.0,
            'amount_total_tax': 0.0,
            'tax_data_source': False,
            'filing_count': 0,
            'pending_filings': 0,
            'validated_filings': 0,
            'generated_filings': 0,
            'submitted_filings': 0,
            'filed_filings': 0,
            'filing_errors': 0,
            'total_2b_records': 0,
            'exact_matches': 0,
            'partial_matches': 0,
            'mismatches': 0,
            'missing_in_books': 0,
            'missing_in_2b': 0,
            'manual_review': 0,
            'validated_documents': 0,
            'validation_errors': 0,
            'validation_warnings': 0,
            'blocking_errors': 0,
            'unvalidated_documents': 0,
            'open_exceptions': 0,
            'critical_exceptions': 0,
            'high_exceptions': 0,
            'resolved_exceptions': 0,
            'eligible_itc': 0.0,
            'reconciled_itc': 0.0,
            'unreconciled_itc': 0.0,
            'einvoice_total': 0,
            'einvoice_generated': 0,
            'einvoice_cancelled': 0,
            'einvoice_failed': 0,
            'einvoice_pending': 0,
            'ewaybill_total': 0,
            'ewaybill_generated': 0,
            'ewaybill_active': 0,
            'ewaybill_expired': 0,
            'ewaybill_cancelled': 0,
            'ewaybill_pending': 0,
        }

    def _vals_from_dashboard_data(self, data):
        """Map service payload into stored KPI field values."""
        vals = self._zero_kpi_vals()
        overview = (data.get('overview') or {}).get('kpis') or {}
        tax = (data.get('tax_summary') or {}).get('kpis') or {}
        filing = (data.get('filing') or {}).get('kpis') or {}
        recon = (data.get('reconciliation_2b') or {}).get('kpis') or {}
        validation = (data.get('invoice_validation') or {}).get('kpis') or {}
        exceptions = (data.get('exceptions') or {}).get('kpis') or {}
        itc = (data.get('itc') or {}).get('kpis') or {}
        einvoice = (data.get('einvoice') or {}).get('kpis') or {}
        ewaybill = (data.get('ewaybill') or {}).get('kpis') or {}

        vals.update({
            'total_invoices': overview.get('total_invoices') or 0,
            'total_vendor_bills': overview.get('total_vendor_bills') or 0,
            'total_credit_notes': overview.get('total_credit_notes') or 0,
            'total_debit_notes': overview.get('total_debit_notes') or 0,
            'taxable_value': tax.get('taxable_value') or overview.get('taxable_value') or 0.0,
            'amount_cgst': tax.get('cgst') or overview.get('cgst') or 0.0,
            'amount_sgst': tax.get('sgst') or overview.get('sgst') or 0.0,
            'amount_igst': tax.get('igst') or overview.get('igst') or 0.0,
            'amount_cess': tax.get('cess') or overview.get('cess') or 0.0,
            'amount_total_tax': tax.get('total_tax') or overview.get('total_tax') or 0.0,
            'tax_data_source': tax.get('source') or False,
            'filing_count': filing.get('filing_count') or 0,
            'pending_filings': filing.get('pending_filings') or 0,
            'validated_filings': filing.get('validated_filings') or 0,
            'generated_filings': filing.get('generated_filings') or 0,
            'submitted_filings': filing.get('submitted_filings') or 0,
            'filed_filings': filing.get('filed_filings') or 0,
            'filing_errors': filing.get('filing_errors') or 0,
            'total_2b_records': recon.get('total_2b_records') or 0,
            'exact_matches': recon.get('exact_matches') or 0,
            'partial_matches': recon.get('partial_matches') or 0,
            'mismatches': recon.get('mismatches') or 0,
            'missing_in_books': recon.get('missing_in_books') or 0,
            'missing_in_2b': recon.get('missing_in_2b') or 0,
            'manual_review': recon.get('manual_review') or 0,
            'validated_documents': validation.get('validated_documents') or 0,
            'validation_errors': validation.get('validation_errors') or 0,
            'validation_warnings': validation.get('validation_warnings') or 0,
            'blocking_errors': validation.get('blocking_errors') or 0,
            'unvalidated_documents': validation.get('unvalidated_documents') or 0,
            'open_exceptions': exceptions.get('open_exceptions') or 0,
            'critical_exceptions': exceptions.get('critical_exceptions') or 0,
            'high_exceptions': exceptions.get('high_exceptions') or 0,
            'resolved_exceptions': exceptions.get('resolved_exceptions') or 0,
            'eligible_itc': itc.get('eligible_itc') or 0.0,
            'reconciled_itc': itc.get('reconciled_itc') or 0.0,
            'unreconciled_itc': itc.get('unreconciled_itc') or 0.0,
            'einvoice_total': einvoice.get('total') or 0,
            'einvoice_generated': einvoice.get('generated') or 0,
            'einvoice_cancelled': einvoice.get('cancelled') or 0,
            'einvoice_failed': einvoice.get('failed') or 0,
            'einvoice_pending': einvoice.get('pending') or 0,
            'ewaybill_total': ewaybill.get('total') or 0,
            'ewaybill_generated': ewaybill.get('generated') or 0,
            'ewaybill_active': ewaybill.get('active') or 0,
            'ewaybill_expired': ewaybill.get('expired') or 0,
            'ewaybill_cancelled': ewaybill.get('cancelled') or 0,
            'ewaybill_pending': ewaybill.get('pending') or 0,
        })
        return vals

    def _refresh_kpis(self):
        for rec in self:
            data = svc.get_dashboard_data(rec.env, rec._filters_dict())
            vals = rec._vals_from_dashboard_data(data)
            vals.update({
                'last_refresh': fields.Datetime.now(),
                'refreshed_by': self.env.user.id,
            })
            # Avoid recursion on create: write without triggering create again.
            super(ArmoraGstDashboard, rec).write(vals)

    @api.model
    def action_open_dashboard(self):
        """Open or create a workspace dashboard for the current company."""
        company = self.env.company
        dash = self.search([
            ('company_id', '=', company.id),
            ('active', '=', True),
            ('create_uid', '=', self.env.user.id),
        ], limit=1, order='id desc')
        if not dash:
            today = fields.Date.context_today(self)
            period = self.env['armora.gst.period']
            fy = period.current_financial_year(today)
            rp = '%02d' % today.month
            vals = {
                'company_id': company.id,
                'financial_year': fy,
                'return_period': rp,
                'gstin': (company.vat or '').upper().strip() or False,
            }
            try:
                start, end = period.compute_period_dates(fy, rp, 'monthly')
                vals['date_from'] = start
                vals['date_to'] = end
            except ValidationError:
                pass
            dash = self.create(vals)
        else:
            dash._refresh_kpis()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GST Dashboard'),
            'res_model': 'armora.gst.dashboard',
            'view_mode': 'form',
            'res_id': dash.id,
            'target': 'current',
        }

    def action_refresh(self):
        self._refresh_kpis()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'armora.gst.dashboard',
            'view_mode': 'form',
            'res_id': self[:1].id,
            'target': 'current',
        }

    def action_open_filter_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dashboard Filters'),
            'res_model': 'armora.gst.dashboard.filter.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_dashboard_id': self.id,
                'default_company_id': self.company_id.id,
                'default_gst_registration_id': self.gst_registration_id.id,
                'default_gstin': self.gstin,
                'default_financial_year': self.financial_year,
                'default_return_period': self.return_period,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            },
        }
