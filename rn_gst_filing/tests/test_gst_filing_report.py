# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGstFilingReport(RnGstFilingTestCommon):

    def test_gstr1_summary_data_and_pdf(self):
        invoice = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            invoice_date='2025-04-15',
        )
        invoice.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        invoice.action_post()
        credit_note = self.init_invoice(
            move_type='out_refund',
            partner=self.partner_a,
            amounts=[400.0],
            taxes=self.sgst_sale_18,
            invoice_date='2025-04-20',
        )
        credit_note.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        credit_note.action_post()
        filing = self._create_gst_filing('04')
        filing.action_load_data()

        data = filing._get_gstr1_report_data()
        sections = {row['key']: row for row in data['sections']}
        self.assertEqual(len(sections), 7)
        self.assertEqual(sections['b2b']['documents'], 1)
        self.assertAlmostEqual(sections['b2b']['taxable_value'], 1000.0)
        self.assertAlmostEqual(sections['b2b']['cgst_amount'], 90.0)
        self.assertAlmostEqual(sections['b2b']['sgst_amount'], 90.0)
        self.assertAlmostEqual(sections['b2cs']['taxable_value'], 0.0)
        self.assertAlmostEqual(data['net']['total_tax'], filing.amount_total_tax)
        # HSN summary is net of the credit note.
        self.assertEqual(len(data['hsn_rows']), 1)
        self.assertEqual(data['hsn_rows'][0]['hsn'], '998314')
        self.assertAlmostEqual(data['hsn_rows'][0]['taxable_value'], 600.0)
        self.assertAlmostEqual(data['hsn_rows'][0]['cgst_amount'], 54.0)

        html = self.env['ir.actions.report']._render_qweb_html(
            'rn_gst_filing.report_gstr1_summary', filing.ids,
        )[0].decode()
        self.assertIn('GSTR-1 Summary', html)
        self.assertIn(filing.gstin, html)
        self.assertIn('HSN-wise summary', html)
