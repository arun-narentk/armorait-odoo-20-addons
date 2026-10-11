# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstRcm(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_rcm.group_rn_gst_rcm_manager').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        chart = cls.env['account.chart.template']
        cls.gst_rc_5 = chart.ref('sgst_purchase_5_rc')
        cls.igst_rc_5 = chart.ref('igst_purchase_5_rc')
        cls.transport = cls.env['product.category'].create({'name': 'Transport'})
        cls.freight = cls.env['product.product'].create({
            'name': 'Freight by road', 'type': 'service', 'categ_id': cls.transport.id, 'l10n_in_hsn_code': '996511',
        })
        cls.gta = cls.env.ref('rn_gst_rcm.rcm_rule_gta')
        cls.gta.write({
            'categ_ids': [(6, 0, cls.transport.ids)],
            'tax_intra_id': cls.gst_rc_5.id,
            'tax_inter_id': cls.igst_rc_5.id,
        })
        cls.default_company.external_report_layout_id = cls.env.ref('web.external_layout_standard')
        cls.truck_owner = cls.env['res.partner'].create({
            'name': 'Local Truck Owner',
            'state_id': cls.state_in_gj.id,
            'country_id': cls.country_in.id,
            'l10n_in_gst_treatment': 'unregistered',
        })

    def _draft_bill(self, partner, invoice_date='2025-04-10'):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.freight.id, 'quantity': 1, 'price_unit': 1000.0, 'tax_ids': [(6, 0, [])],
            })],
        })
        bill.invoice_line_ids.l10n_in_hsn_code = '996511'
        return bill

    def test_rcm_bill_flow(self):
        bill = self._draft_bill(self.truck_owner)
        self.assertTrue(bill.rn_rcm_missing)
        self.assertIn(self.gta.name, bill.rn_rcm_missing_note)
        bill.action_rn_apply_rcm()
        self.assertEqual(bill.invoice_line_ids.tax_ids, self.gst_rc_5)
        self.assertFalse(bill.rn_rcm_missing)
        self.assertTrue(bill.rn_is_rcm)

        # A supplier in another state gets the IGST reverse charge tax.
        inter = self._draft_bill(self.partner_b)
        inter.action_rn_apply_rcm()
        self.assertEqual(inter.invoice_line_ids.tax_ids, self.igst_rc_5)

        bill.action_post()
        self.assertEqual(bill.rn_rcm_supply_type, 'services')
        self.assertAlmostEqual(bill.rn_rcm_tax, 50.0)
        # Unpaid service: tax falls due on the 61st day after the invoice.
        self.assertEqual(bill.rn_rcm_tos_date, date(2025, 6, 10))
        self.assertEqual(bill.rn_rcm_tos_period, '2025-06')
        self.assertTrue(bill.rn_self_invoice_required)
        self.assertEqual(bill.rn_self_invoice_due, date(2025, 5, 10))
        action = bill.action_rn_issue_self_invoice()
        self.assertTrue(bill.rn_self_invoice_number.startswith('SI/'))
        self.assertEqual(action['report_name'], 'rn_gst_rcm.report_self_invoice')
        number = bill.rn_self_invoice_number
        bill.action_rn_issue_self_invoice()
        self.assertEqual(bill.rn_self_invoice_number, number, 'Issuing again keeps the same number.')
        html = self.env['ir.actions.report']._render_qweb_html('rn_gst_rcm.report_self_invoice', bill.ids)[0].decode()
        self.assertIn(number, html)
        self.assertIn('Local Truck Owner', html)
        self.assertIn('Freight by road', html)

        # A registered supplier needs no self-invoice.
        self.assertFalse(inter.rn_self_invoice_required)
        with self.assertRaises(UserError):
            inter.action_rn_issue_self_invoice()

    def test_time_of_supply_payment(self):
        bill = self._draft_bill(self.truck_owner)
        bill.action_rn_apply_rcm()
        bill.action_post()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({'payment_date': '2025-04-20'})._create_payments()
        self.assertEqual(bill.rn_rcm_payment_date, date(2025, 4, 20))
        self.assertEqual(bill.rn_rcm_tos_date, date(2025, 4, 20))

    def test_gstr3b_warns_on_time_of_supply(self):
        if 'rn.gst.3b' not in self.env:
            self.skipTest('Armora GST GSTR-3B is not installed.')
        bill = self._draft_bill(self.truck_owner)
        bill.action_rn_apply_rcm()
        bill.action_post()
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
        self.assertIn('falls due in a later month', gstr3b.books_warning)
        self.assertIn(bill.name, gstr3b.books_warning)
