# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGst3bBooks(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_base.group_rn_gst_administrator').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            # Test documents carry no shipping bill or port code; do not block posting.
            cls.default_company.rn_gst_block_post_on_error = False
        chart = cls.env['account.chart.template']
        cls.exempt_sale = chart.ref('exempt_sale')
        cls.exempt_purchase = chart.ref('exempt_purchase')
        cls.igst_purchase_18_rc = chart.ref('igst_purchase_18_rc')
        cls.consumer_mh = cls.env['res.partner'].create({
            'name': 'Walk-in Customer Maharashtra',
            'state_id': cls.state_in_mh.id,
            'country_id': cls.country_in.id,
            'l10n_in_gst_treatment': 'consumer',
        })

    def _post(self, move_type, partner, amount, taxes):
        move = self.init_invoice(
            move_type=move_type, partner=partner, amounts=[amount], taxes=taxes, invoice_date='2025-04-15',
        )
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _create_3b(self):
        return self.env['rn.gst.3b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'period_start': '2025-04-01',
            'period_end': '2025-04-30',
            'due_date': '2025-05-20',
            'payment_date': '2025-05-20',
        })

    def test_fill_from_books(self):
        self._post('out_invoice', self.partner_a, 1000.0, self.sgst_sale_18)
        self._post('out_invoice', self.partner_foreign, 1000.0, self.igst_sale_18_exp)
        self._post('out_invoice', self.partner_foreign, 500.0, self.igst_sale_18_exp_lut)
        self._post('out_invoice', self.partner_a, 200.0, self.exempt_sale)
        self._post('out_invoice', self.partner_b, 300.0, self.igst_sale_18_rcm)
        self._post('out_invoice', self.consumer_mh, 400.0, self.igst_sale_18)
        self._post('in_invoice', self.partner_a, 1000.0, self.sgst_purchase_5)
        self._post('in_invoice', self.partner_b, 1000.0, self.igst_purchase_18_rc)
        self._post('in_invoice', self.partner_b, 100.0, self.exempt_purchase)

        gstr3b = self._create_3b()
        gstr3b.action_fill_from_books()

        # 3.1(a): intra-state B2B and the inter-state consumer sale. The reverse
        # charge sale is reported by the buyer and is in no row of Table 3.1.
        self.assertAlmostEqual(gstr3b.t31a_taxable, 1400.0)
        self.assertAlmostEqual(gstr3b.t31a_cgst, 90.0)
        self.assertAlmostEqual(gstr3b.t31a_sgst, 90.0)
        self.assertAlmostEqual(gstr3b.t31a_igst, 72.0)
        # 3.1(b): export with payment of IGST plus export under LUT (no tax).
        self.assertAlmostEqual(gstr3b.t31b_taxable, 1500.0)
        self.assertAlmostEqual(gstr3b.t31b_igst, 180.0)
        self.assertAlmostEqual(gstr3b.t31c_taxable, 200.0)
        self.assertAlmostEqual(gstr3b.t31e_taxable, 0.0)
        # 3.1(d) and 4(A)(3): reverse charge purchase.
        self.assertAlmostEqual(gstr3b.t31d_taxable, 1000.0)
        self.assertAlmostEqual(gstr3b.t31d_igst, 180.0)
        self.assertAlmostEqual(gstr3b.t4a3_igst, 180.0)
        # 4(A)(5): regular purchase.
        self.assertAlmostEqual(gstr3b.t4a5_cgst, 25.0)
        self.assertAlmostEqual(gstr3b.t4a5_sgst, 25.0)
        self.assertAlmostEqual(gstr3b.t4c_igst, 180.0)
        self.assertAlmostEqual(gstr3b.t4c_cgst, 25.0)
        # 5: exempt purchase from another state.
        self.assertAlmostEqual(gstr3b.t5_exempt_inter, 100.0)
        self.assertAlmostEqual(gstr3b.t5_exempt_intra, 0.0)
        # 3.2: consumer in Maharashtra.
        self.assertEqual(len(gstr3b.interstate_line_ids), 1)
        line = gstr3b.interstate_line_ids
        self.assertEqual((line.supply_type, line.state_id), ('unregistered', self.state_in_mh))
        self.assertAlmostEqual(line.taxable_value, 400.0)
        self.assertAlmostEqual(line.igst, 72.0)

        # Table 6.1: forward charge liability is set off against net ITC; the
        # reverse charge tax is added to cash because it cannot use ITC.
        self.assertAlmostEqual(gstr3b.liability_igst, 252.0)
        self.assertAlmostEqual(gstr3b.liability_cgst, 90.0)
        self.assertAlmostEqual(gstr3b.itc_available_igst, 180.0)
        self.assertAlmostEqual(gstr3b.itc_available_cgst, 25.0)
        self.assertAlmostEqual(gstr3b.itc_utilized_igst, 180.0)
        self.assertAlmostEqual(gstr3b.cash_payable_igst, 72.0 + 180.0)
        self.assertAlmostEqual(gstr3b.cash_payable_cgst, 65.0)
        self.assertAlmostEqual(gstr3b.cash_payable_sgst, 65.0)
        self.assertAlmostEqual(gstr3b.net_tax_liability, 252.0 + 65.0 + 65.0)
        self.assertEqual(gstr3b.state, 'computed')
        self.assertFalse(gstr3b.books_warning)

        # Refill keeps hand-entered rows and does not double the numbers.
        gstr3b.t4b2_cgst = 5.0
        gstr3b.action_fill_from_books()
        self.assertAlmostEqual(gstr3b.t31a_taxable, 1400.0)
        self.assertAlmostEqual(gstr3b.t4b2_cgst, 5.0)
        self.assertAlmostEqual(gstr3b.t4c_cgst, 20.0)
        self.assertEqual(len(gstr3b.interstate_line_ids), 1)

        html = self.env['ir.actions.report']._render_qweb_html(
            'rn_gst_3b.report_gstr3b_summary', gstr3b.ids,
        )[0].decode()
        self.assertIn('Table 3.1', html)
        self.assertIn('Table 3.2', html)
        self.assertIn('Maharashtra', html)

    def test_fill_from_books_refused_when_filed(self):
        gstr3b = self._create_3b()
        gstr3b.action_mark_filed()
        with self.assertRaises(UserError):
            gstr3b.action_fill_from_books()
