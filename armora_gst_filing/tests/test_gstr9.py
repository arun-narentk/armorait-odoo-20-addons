# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


class ArmoraGstr9Common(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for xmlid in ('armora_gst_filing.group_armora_gst_filing_manager', 'armora_gst_base.group_armora_gst_administrator'):
            cls.env.user.group_ids = [(4, cls.env.ref(xmlid).id)]
        if 'armora_gst_block_post_on_error' in cls.default_company._fields:
            # Test documents carry no shipping bill or original invoice; do not block posting.
            cls.default_company.armora_gst_block_post_on_error = False
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

    def _post(self, move_type, partner, amount, taxes, invoice_date='2025-04-15'):
        move = self.init_invoice(
            move_type=move_type, partner=partner, amounts=[amount], taxes=taxes, invoice_date=invoice_date,
        )
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _post_year(self):
        self._post('out_invoice', self.partner_a, 1000.0, self.sgst_sale_18)
        self._post('out_invoice', self.partner_foreign, 1000.0, self.igst_sale_18_exp)
        self._post('out_invoice', self.partner_foreign, 500.0, self.igst_sale_18_exp_lut)
        self._post('out_invoice', self.partner_a, 200.0, self.exempt_sale)
        self._post('out_invoice', self.partner_b, 300.0, self.igst_sale_18_rcm)
        self._post('out_invoice', self.consumer_mh, 400.0, self.igst_sale_18)
        self._post('out_refund', self.partner_a, 100.0, self.sgst_sale_18, invoice_date='2025-04-20')
        self._post('in_invoice', self.partner_a, 1000.0, self.sgst_purchase_5)
        self._post('in_invoice', self.partner_b, 1000.0, self.igst_purchase_18_rc)
        self._post('in_invoice', self.partner_b, 100.0, self.exempt_purchase)

    def _create_gstr9(self):
        return self.env['armora.gst.gstr9'].create({
            'company_id': self.default_company.id,
            'financial_year': '2025-26',
        })


@tagged('post_install', '-at_install')
class TestArmoraGstr9(ArmoraGstr9Common):

    def test_fill_from_books(self):
        self._post_year()
        gstr9 = self._create_gstr9()
        self.assertEqual(gstr9.gstin, self.default_company.vat)
        self.assertEqual((str(gstr9.date_from), str(gstr9.date_to)), ('2025-04-01', '2026-03-31'))
        gstr9.action_fill_from_books()

        def row(code):
            return gstr9._armora_row(code)

        self.assertAlmostEqual(row('4A').value, 400.0)
        self.assertAlmostEqual(row('4A').igst, 72.0)
        self.assertAlmostEqual(row('4B').value, 1000.0)
        self.assertAlmostEqual(row('4B').cgst, 90.0)
        self.assertAlmostEqual(row('4C').value, 1000.0)
        self.assertAlmostEqual(row('4C').igst, 180.0)
        self.assertAlmostEqual(row('4G').value, 1000.0)
        self.assertAlmostEqual(row('4G').igst, 180.0)
        # The credit note is shown as a positive amount in 4I and subtracted in 4M.
        self.assertAlmostEqual(row('4I').value, 100.0)
        self.assertAlmostEqual(row('4I').cgst, 9.0)
        self.assertAlmostEqual(row('4H').value, 3400.0)
        self.assertAlmostEqual(row('4N').value, 3300.0)
        self.assertAlmostEqual(row('4N').cgst, 81.0)
        self.assertAlmostEqual(row('5A').value, 500.0)
        self.assertAlmostEqual(row('5C').value, 300.0)
        self.assertAlmostEqual(row('5D').value, 200.0)
        self.assertAlmostEqual(row('5M').value, 1000.0)
        # Total turnover: 4N + 5M - 4G.
        self.assertAlmostEqual(row('5N').value, 3300.0)
        self.assertAlmostEqual(row('6B1').cgst, 25.0)
        self.assertAlmostEqual(row('6D').igst, 180.0)
        self.assertAlmostEqual(row('6I').igst, 180.0)
        self.assertAlmostEqual(row('6I').cgst, 25.0)
        # No import of goods in this year: nothing to lapse on imports.
        self.assertAlmostEqual(row('8I').igst, 0.0)
        self.assertAlmostEqual(row('8K').igst, 0.0)

        outward = gstr9.hsn_outward_ids
        self.assertAlmostEqual(sum(outward.mapped('taxable_value')), 3300.0)
        # IGST on HSN 998314: export with payment 180 + consumer 72 + reverse charge sale 54; the LUT export pays none.
        self.assertAlmostEqual(sum(outward.mapped('igst')), 306.0)
        self.assertAlmostEqual(sum(gstr9.hsn_inward_ids.mapped('taxable_value')), 2100.0)

        # A manual row is kept on refill and the totals follow it.
        row('4K').write({'value': 50.0})
        self.assertAlmostEqual(row('4N').value, 3350.0)
        gstr9.action_fill_from_books()
        self.assertAlmostEqual(row('4K').value, 50.0)
        self.assertAlmostEqual(row('4N').value, 3350.0)
        self.assertAlmostEqual(row('4B').value, 1000.0)

        html = self.env['ir.actions.report']._render_qweb_html('armora_gst_filing.report_gstr9', gstr9.ids)[0].decode()
        self.assertIn('GSTR-9 Annual Return', html)
        self.assertIn('Table 17', html)
        # Rows and HSN lines reach the sub-templates.
        self.assertIn('Supplies made to registered persons (B2B)', html)
        self.assertIn('998314', html)
        self.assertIn('Paid via IGST', html)

        gstr9.action_mark_filed()
        with self.assertRaises(UserError):
            row('4K').write({'value': 60.0})
        with self.assertRaises(UserError):
            gstr9.action_fill_from_books()
