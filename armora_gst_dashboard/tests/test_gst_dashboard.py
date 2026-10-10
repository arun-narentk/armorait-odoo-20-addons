# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

from odoo.addons.armora_gst_dashboard.services import gst_dashboard_service as svc


@tagged('post_install', '-at_install')
class TestArmoraGstDashboard(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = [
            'armora_gst_dashboard.group_armora_gst_dashboard_user',
            'armora_gst_dashboard.group_armora_gst_dashboard_manager',
            'armora_gst_base.group_armora_gst_manager',
        ]
        # Soft specialist groups so KPI seed data can be created when modules exist.
        for xmlid in (
            'armora_gst_filing.group_armora_gst_filing_manager',
            'armora_gst_2b_reconciliation.group_armora_gst_2b_manager',
            'armora_gst_invoice_validator.group_armora_gst_validator_manager',
        ):
            groups.append(xmlid)
        for xmlid in groups:
            group = cls.env.ref(xmlid, raise_if_not_found=False)
            if group:
                cls.env.user.group_ids = [(4, group.id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.Dashboard = cls.env['armora.gst.dashboard']

    def _create_dash(self, period='08'):
        return self.Dashboard.create({
            'company_id': self.default_company.id,
            'financial_year': '2025-26',
            'return_period': period,
            'gstin': self.default_company.vat,
            'date_from': '2025-08-01',
            'date_to': '2025-08-31',
        })

    def test_create_dashboard_workspace(self):
        dash = self._create_dash()
        self.assertTrue(dash.name)
        self.assertNotEqual(dash.name, 'New')
        self.assertEqual(dash.company_id, self.default_company)
        self.assertTrue(dash.last_refresh)

    def test_action_open_dashboard(self):
        action = self.Dashboard.action_open_dashboard()
        self.assertEqual(action['res_model'], 'armora.gst.dashboard')
        self.assertTrue(action.get('res_id'))

    def test_module_availability_keys(self):
        availability = svc.module_availability(self.env)
        for key in (
            'filing',
            'reconciliation_2b',
            'invoice_validation',
            'itc',
            'einvoice',
            'ewaybill',
            'exceptions',
        ):
            self.assertIn(key, availability)
            self.assertIsInstance(availability[key], bool)

    def test_get_dashboard_data_structure(self):
        data = svc.get_dashboard_data(self.env, {
            'company_id': self.default_company.id,
            'financial_year': '2025-26',
            'return_period': '08',
            'date_from': '2025-08-01',
            'date_to': '2025-08-31',
            'gstin': self.default_company.vat,
        })
        self.assertIn('overview', data)
        self.assertIn('tax_summary', data)
        self.assertIn('module_availability', data)
        self.assertIn('kpis', data['overview'])

    def test_refresh_sets_audit_fields(self):
        dash = self._create_dash()
        first = dash.last_refresh
        dash.action_refresh()
        self.assertTrue(dash.last_refresh)
        self.assertEqual(dash.refreshed_by, self.env.user)
        self.assertGreaterEqual(dash.last_refresh, first)

    def test_optional_sections_zero_when_unavailable(self):
        dash = self._create_dash()
        availability = svc.module_availability(self.env)
        if not availability.get('itc'):
            self.assertFalse(dash.module_itc_available)
            self.assertEqual(dash.eligible_itc, 0.0)
        if not availability.get('exceptions'):
            self.assertFalse(dash.module_exception_available)
            self.assertEqual(dash.open_exceptions, 0)

    def test_filing_kpis_when_module_present(self):
        if 'armora.gst.filing' not in self.env:
            self.skipTest('armora_gst_filing not installed')
        start, end = self.env['armora.gst.period'].compute_period_dates(
            '2025-26', '08', 'monthly',
        )
        filing = self.env['armora.gst.filing'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '08',
            'filing_type': 'gstr1',
            'filing_frequency': 'monthly',
            'period_start': start,
            'period_end': end,
            'state': 'validated',
            'validation_error_count': 3,
        })
        dash = self._create_dash('08')
        self.assertTrue(dash.module_filing_available)
        self.assertGreaterEqual(dash.filing_count, 1)
        self.assertGreaterEqual(dash.validated_filings, 1)
        self.assertGreaterEqual(dash.filing_errors, 3)
        self.assertEqual(filing.company_id, self.default_company)

    def test_2b_kpis_when_module_present(self):
        if 'armora.gst.gstr2b' not in self.env:
            self.skipTest('armora_gst_2b_reconciliation not installed')
        start, end = self.env['armora.gst.period'].compute_period_dates(
            '2025-26', '08', 'monthly',
        )
        recon = self.env['armora.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '08',
            'filing_frequency': 'monthly',
            'period_start': start,
            'period_end': end,
        })
        self.env['armora.gst.gstr2b.line'].create({
            'reconciliation_id': recon.id,
            'source': 'gstr2b',
            'match_state': 'matched',
            'vendor_gstin': '24AAPFU0939F1Z1',
            'invoice_number': 'BILL-1',
            'invoice_date': start,
            'taxable_value': 1000.0,
            'sgst_amount': 50.0,
        })
        self.env['armora.gst.gstr2b.line'].create({
            'reconciliation_id': recon.id,
            'source': 'gstr2b',
            'match_state': 'mismatch',
            'vendor_gstin': '24AAPFU0939F1Z1',
            'invoice_number': 'BILL-2',
            'invoice_date': start,
            'taxable_value': 500.0,
            'sgst_amount': 25.0,
        })
        recon._compute_dashboard()
        dash = self._create_dash('08')
        self.assertTrue(dash.module_2b_available)
        self.assertGreaterEqual(dash.exact_matches, 1)
        self.assertGreaterEqual(dash.mismatches, 1)

    def test_does_not_invent_itc(self):
        dash = self._create_dash()
        if not dash.module_itc_available:
            self.assertEqual(dash.eligible_itc, 0.0)
            self.assertEqual(dash.reconciled_itc, 0.0)
            self.assertEqual(dash.unreconciled_itc, 0.0)
