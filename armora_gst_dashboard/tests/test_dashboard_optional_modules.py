# -*- coding: utf-8 -*-
"""Optional-module degradation tests."""
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

from odoo.addons.armora_gst_dashboard.services import gst_dashboard_service as svc


@tagged('post_install', '-at_install')
class TestArmoraGstDashboardOptionalModules(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [
            (4, cls.env.ref('armora_gst_dashboard.group_armora_gst_dashboard_user').id),
        ]

    def test_disabled_sections_do_not_crash(self):
        availability = {
            'filing': False,
            'reconciliation_2b': False,
            'invoice_validation': False,
            'itc': False,
            'einvoice': False,
            'ewaybill': False,
            'exceptions': False,
        }
        filters = {'company_id': self.env.company.id}
        # Direct provider calls with forced unavailable flags.
        from odoo.addons.armora_gst_dashboard.services import (
            gst_dashboard_2b,
            gst_dashboard_einvoice,
            gst_dashboard_ewaybill,
            gst_dashboard_exceptions,
            gst_dashboard_filings,
            gst_dashboard_itc,
            gst_dashboard_validation,
        )
        for getter in (
            gst_dashboard_filings.get_filing_stats,
            gst_dashboard_2b.get_2b_stats,
            gst_dashboard_validation.get_validation_stats,
            gst_dashboard_itc.get_itc_stats,
            gst_dashboard_einvoice.get_einvoice_stats,
            gst_dashboard_ewaybill.get_ewaybill_stats,
            gst_dashboard_exceptions.get_exception_stats,
        ):
            section = getter(self.env, filters, availability)
            self.assertFalse(section['available'])
            self.assertTrue(section.get('message'))

    def test_facade_survives_base_only(self):
        data = svc.get_dashboard_data(self.env, {
            'company_id': self.env.company.id,
            'financial_year': '2025-26',
            'return_period': '08',
        })
        self.assertIn('module_availability', data)
        self.assertIsInstance(data['filing']['available'], bool)
