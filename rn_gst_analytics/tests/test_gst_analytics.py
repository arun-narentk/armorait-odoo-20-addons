# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstAnalytics(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_base.group_rn_gst_user').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.igst_purchase_18 = cls.env['account.chart.template'].ref('igst_purchase_18')

    def _post(self, move_type, partner, amount, taxes, date='2025-04-10'):
        move = self.init_invoice(move_type, partner=partner, amounts=[amount], taxes=taxes, invoice_date=date)
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _rows(self, moves):
        self.env.flush_all()
        return self.env['rn.gst.analytics'].search([('move_id', 'in', moves.ids)])

    def test_outward_and_inward(self):
        sale = self._post('out_invoice', self.partner_a, 1000.0, self.sgst_sale_18)
        refund = self._post('out_refund', self.partner_a, 200.0, self.sgst_sale_18)
        bill = self._post('in_invoice', self.partner_b, 500.0, self.igst_purchase_18)
        rows = self._rows(sale | refund | bill)

        sale_rows = rows.filtered(lambda r: r.move_id == sale)
        taxable = sale_rows.filtered(lambda r: r.kind == 'taxable')
        self.assertEqual(len(taxable), 1, 'Taxable value of a CGST+SGST line is counted once.')
        self.assertEqual((taxable.head, taxable.taxable_amount, taxable.direction), ('cgst_sgst', 1000.0, 'outward'))
        self.assertEqual(sorted(sale_rows.filtered(lambda r: r.kind == 'tax').mapped('head')), ['cgst', 'sgst'])
        self.assertAlmostEqual(sum(sale_rows.mapped('output_tax')), 180.0)

        refund_rows = rows.filtered(lambda r: r.move_id == refund)
        self.assertAlmostEqual(sum(refund_rows.mapped('taxable_amount')), -200.0)
        self.assertAlmostEqual(sum(refund_rows.mapped('output_tax')), -36.0)

        bill_rows = rows.filtered(lambda r: r.move_id == bill)
        self.assertEqual(set(bill_rows.mapped('head')), {'igst'})
        self.assertAlmostEqual(sum(bill_rows.mapped('input_tax')), 90.0)
        self.assertAlmostEqual(sum(bill_rows.mapped('taxable_amount')), 500.0)

    def test_reverse_charge_sale_not_output_tax(self):
        rcm = self._post('out_invoice', self.partner_a, 1000.0, self.igst_sale_18_rcm)
        rows = self._rows(rcm)
        self.assertEqual(sum(rows.mapped('output_tax')), 0.0)
        self.assertEqual(sum(rows.mapped('taxable_amount')), 1000.0)

    def test_draft_not_counted_and_grouping(self):
        draft = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], taxes=self.sgst_sale_18,
                                  invoice_date='2025-04-10')
        self.assertFalse(self._rows(draft))
        sale = self._post('out_invoice', self.partner_a, 1000.0, self.sgst_sale_18)
        self.env.flush_all()
        groups = self.env['rn.gst.analytics']._read_group(
            [('move_id', '=', sale.id)], ['direction', 'kind'], ['taxable_amount:sum', 'tax_amount:sum'])
        totals = {(d, k): (t, x) for d, k, t, x in groups}
        self.assertEqual(totals[('outward', 'taxable')][0], 1000.0)
        self.assertAlmostEqual(totals[('outward', 'tax')][1], 180.0)
