# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstBasePeriod(L10nInTestInvoicingCommon):

    def test_monthly_april(self):
        start, end = self.env['rn.gst.filing.period'].compute_period_dates('2025-26', '04', 'monthly')
        self.assertEqual(start, date(2025, 4, 1))
        self.assertEqual(end, date(2025, 4, 30))

    def test_monthly_january_next_calendar_year(self):
        start, end = self.env['rn.gst.filing.period'].compute_period_dates('2025-26', '01', 'monthly')
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 1, 31))

    def test_quarter_q1(self):
        start, end = self.env['rn.gst.filing.period'].compute_period_dates('2025-26', 'Q1', 'quarterly')
        self.assertEqual(start, date(2025, 4, 1))
        self.assertEqual(end, date(2025, 6, 30))

    def test_invalid_fy(self):
        with self.assertRaises(ValidationError):
            self.env['rn.gst.filing.period'].compute_period_dates('bad', '04', 'monthly')
