# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGstCalculation(RnGstFilingTestCommon):

    def test_tax_exclusive_amounts(self):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-10',
        )
        Extractor = self.env['rn.gst.data.extractor']
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        info = Extractor._tax_amounts_for_line(move, line)
        self.assertAlmostEqual(info['taxable_value'], 1000.0, places=2)
        self.assertAlmostEqual(info['gst_rate'], 18.0, places=2)
        self.assertAlmostEqual(info['cgst_amount'] + info['sgst_amount'], 180.0, places=2)

    def test_multiple_lines(self):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_b,
            amounts=[500.0, 1500.0],
            taxes=self.igst_sale_18,
            post=True,
            invoice_date='2025-04-10',
        )
        Extractor = self.env['rn.gst.data.extractor']
        total = 0.0
        for line in move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product')):
            total += Extractor._tax_amounts_for_line(move, line)['taxable_value']
        self.assertAlmostEqual(total, 2000.0, places=2)

    def test_discount(self):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=False,
            invoice_date='2025-04-10',
        )
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        line.discount = 10.0
        move.action_post()
        info = self.env['rn.gst.data.extractor']._tax_amounts_for_line(move, line)
        self.assertAlmostEqual(info['taxable_value'], 900.0, places=2)

    def test_offset_taxes_counted_once(self):
        """Export and reverse charge taxes post +100%/-100% lines; report the IGST once."""
        company_id = self.default_company.id
        for xmlid in ('igst_sale_18_exp', 'igst_sale_18_rc'):
            with self.subTest(tax=xmlid):
                tax = self.env.ref('account.%s_%s' % (company_id, xmlid))
                move = self.init_invoice(
                    move_type='out_invoice',
                    partner=self.partner_b,
                    amounts=[1000.0],
                    taxes=tax,
                    post=True,
                    invoice_date='2025-04-10',
                )
                line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
                info = self.env['rn.gst.data.extractor']._tax_amounts_for_line(move, line)
                self.assertAlmostEqual(info['igst_amount'], 180.0, places=2)
                self.assertAlmostEqual(info['gst_rate'], 18.0, places=2)
