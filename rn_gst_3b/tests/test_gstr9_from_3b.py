# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.rn_gst_filing.tests.test_gstr9 import RnGstr9Common


@tagged('post_install', '-at_install')
class TestRnGstr9From3b(RnGstr9Common):

    def test_gstr9_uses_gstr3b(self):
        self._post_year()
        gstr3b = self.env['rn.gst.3b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'period_start': '2025-04-01',
            'period_end': '2025-04-30',
            'due_date': '2025-05-20',
            'payment_date': '2025-05-20',
        })
        gstr3b.action_fill_from_books()

        gstr9 = self._create_gstr9()
        gstr9.action_fill_from_books()
        self.assertEqual(gstr9.gstr3b_months, 1)
        self.assertIn('1 of 12', gstr9.fill_warning)

        def row(code):
            return gstr9._rn_row(code)

        # 6A (ITC per GSTR-3B) equals 6I (ITC per books): the difference 6J is zero.
        self.assertAlmostEqual(row('6A').igst, 180.0)
        self.assertAlmostEqual(row('6A').cgst, 25.0)
        self.assertAlmostEqual(row('6J').igst, 0.0)
        self.assertAlmostEqual(row('6J').cgst, 0.0)
        # Table 9: IGST payable is the forward charge liability plus reverse charge tax.
        self.assertAlmostEqual(row('9IGST').value, gstr3b.liability_igst + gstr3b.t31d_igst)
        self.assertAlmostEqual(row('9IGST').cash, gstr3b.cash_payable_igst)
        self.assertAlmostEqual(row('9IGST').igst, gstr3b.itc_utilized_igst)
        self.assertAlmostEqual(row('9CGST').value, gstr3b.liability_cgst)
        paid = row('9CGST').cash + row('9CGST').igst + row('9CGST').cgst + row('9CGST').sgst
        self.assertAlmostEqual(paid, row('9CGST').value)
