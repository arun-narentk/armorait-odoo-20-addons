# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_gstr9 import ArmoraGstr9Common


@tagged('post_install', '-at_install')
class TestArmoraGstr9c(ArmoraGstr9Common):

    def test_fill_from_books(self):
        self._post_year()
        gstr9 = self._create_gstr9()
        gstr9.action_fill_from_books()
        gstr9c = self.env['armora.gst.gstr9c'].create({
            'company_id': self.default_company.id,
            'financial_year': '2025-26',
        })
        gstr9c.action_fill_from_books()
        self.assertEqual(gstr9c.gstr9_id, gstr9)

        def row(code):
            return gstr9c._armora_row(code)

        # Turnover: books and the annual return agree.
        self.assertAlmostEqual(row('5A').value, 3300.0)
        self.assertAlmostEqual(row('5Q').value, 3300.0)
        self.assertAlmostEqual(row('5R').value, 0.0)
        self.assertAlmostEqual(row('7B').value, 200.0)
        self.assertAlmostEqual(row('7C').value, 500.0)
        self.assertAlmostEqual(row('7D').value, 300.0)
        self.assertAlmostEqual(row('7E').value, 2300.0)
        self.assertAlmostEqual(row('7F').value, 2300.0)
        self.assertAlmostEqual(row('7G').value, 0.0)

        # Table 9: one 18% line with outward supplies, the credit note and reverse charge inward.
        self.assertEqual(len(gstr9c.rate_ids), 1)
        rate = gstr9c.rate_ids
        self.assertAlmostEqual(rate.rate, 18.0)
        self.assertAlmostEqual(rate.taxable_value, 3300.0)
        self.assertAlmostEqual(rate.igst, 432.0)
        self.assertAlmostEqual(rate.cgst, 81.0)
        self.assertAlmostEqual(row('9N').igst, 432.0)

        # ITC: books and the annual return agree, on the whole and by expense head.
        self.assertAlmostEqual(row('12A').value, 230.0)
        self.assertAlmostEqual(row('12E').value, 230.0)
        self.assertAlmostEqual(row('12F').value, 0.0)
        self.assertEqual(len(gstr9c.expense_ids), 1)
        self.assertAlmostEqual(gstr9c.expense_ids.expense_value, 2000.0)
        self.assertAlmostEqual(gstr9c.expense_ids.itc_amount, 230.0)
        self.assertAlmostEqual(row('14R').value, 230.0)
        self.assertAlmostEqual(row('14T').value, 0.0)

        # A manual adjustment changes the totals and survives a refill.
        row('5B').write({'value': 100.0})
        self.assertAlmostEqual(row('5P').value, 3400.0)
        self.assertAlmostEqual(row('5R').value, -100.0)
        gstr9c.reason_turnover = 'Unbilled revenue of March booked in April.'
        gstr9c.action_fill_from_books()
        self.assertAlmostEqual(row('5B').value, 100.0)
        self.assertAlmostEqual(row('5R').value, -100.0)
        self.assertEqual(gstr9c.reason_turnover, 'Unbilled revenue of March booked in April.')

        html = self.env['ir.actions.report']._render_qweb_html('armora_gst_filing.report_gstr9c', gstr9c.ids)[0].decode()
        self.assertIn('GSTR-9C Reconciliation Statement', html)
        self.assertIn('Unreconciled turnover', html)
        self.assertIn('Unbilled revenue of March booked in April.', html)

        gstr9c.action_mark_filed()
        with self.assertRaises(UserError):
            row('5B').write({'value': 1.0})

    def test_without_gstr9(self):
        gstr9c = self.env['armora.gst.gstr9c'].create({
            'company_id': self.default_company.id,
            'financial_year': '2025-26',
        })
        gstr9c.action_fill_from_books()
        self.assertIn('No GSTR-9 found', gstr9c.fill_warning)
        self.assertAlmostEqual(gstr9c._armora_row('5Q').value, 0.0)
