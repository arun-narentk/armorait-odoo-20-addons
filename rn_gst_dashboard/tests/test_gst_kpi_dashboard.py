# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstKpiDashboard(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_dashboard.group_rn_gst_dashboard_user').id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.partner_a.write({'vat': '24AAPFU0939F1Z1', 'l10n_in_gst_treatment': 'regular'})
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            # Export test invoices carry no shipping bill; do not block posting on that.
            cls.default_company.rn_gst_block_post_on_error = False

    def test_kpi_payload(self):
        for move_type, taxes, invoice_date in (
            ('out_invoice', self.sgst_sale_18, '2025-04-15'),
            ('in_invoice', self.sgst_purchase_5, '2025-04-20'),
        ):
            move = self.init_invoice(
                move_type=move_type, partner=self.partner_a, amounts=[1000.0],
                taxes=taxes, invoice_date=invoice_date,
            )
            move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
            move.action_post()
        data = self.env['rn.gst.dashboard'].get_kpi_dashboard_data('2025-26', '04')

        kpis = data['kpis']
        self.assertAlmostEqual(kpis['sales_taxable'], 1000.0)
        self.assertAlmostEqual(kpis['purchase_taxable'], 1000.0)
        self.assertAlmostEqual(kpis['output_tax'], 180.0)
        self.assertAlmostEqual(kpis['input_tax'], 50.0)
        self.assertAlmostEqual(kpis['net_payable'], 130.0)
        self.assertEqual(kpis['invoice_count'], 1)
        self.assertEqual(kpis['bill_count'], 1)
        self.assertAlmostEqual(data['output_split']['cgst'], 90.0)
        self.assertAlmostEqual(data['output_split']['sgst'], 90.0)
        self.assertAlmostEqual(data['output_split']['igst'], 0.0)

        self.assertEqual(data['period'], {'date_from': '2025-04-01', 'date_to': '2025-04-30'})
        self.assertEqual(len(data['trend']['months']), 6)
        self.assertEqual(data['trend']['months'][-1], '2025-04-01')
        self.assertAlmostEqual(data['trend']['output_tax'][-1], 180.0)
        due = {row['code']: row['due_date'] for row in data['deadlines']}
        self.assertEqual(due, {'GSTR-1': '2025-05-11', 'GSTR-3B': '2025-05-20'})
        self.assertEqual(data['top_customers'][0]['id'], self.partner_a.id)

    def test_kpi_payload_other_month_is_empty(self):
        data = self.env['rn.gst.dashboard'].get_kpi_dashboard_data('2025-26', '06')
        self.assertEqual(data['kpis']['invoice_count'], 0)
        self.assertEqual(data['top_customers'], [])

    def test_kpi_export_with_payment_counts_lut_does_not(self):
        for taxes in (self.igst_sale_18_exp, self.igst_sale_18_exp_lut):
            self.init_invoice(
                move_type='out_invoice', partner=self.partner_a, amounts=[1000.0],
                taxes=taxes, post=True, invoice_date='2025-05-10',
            )
        data = self.env['rn.gst.dashboard'].get_kpi_dashboard_data('2025-26', '05')
        # Only the export with payment of IGST creates tax payable.
        self.assertAlmostEqual(data['output_split']['igst'], 180.0)
        self.assertAlmostEqual(data['kpis']['output_tax'], 180.0)
        self.assertAlmostEqual(data['kpis']['sales_taxable'], 2000.0)
