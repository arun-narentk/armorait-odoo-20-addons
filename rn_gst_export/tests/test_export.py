# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstExport(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_export.group_rn_gst_export_manager').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'
        cls.port = cls.env['l10n_in.port.code'].create({'code': 'INZZZ9', 'name': 'Test Port'})
        cls.today = fields.Date.today()

    def _export(self, taxes, invoice_date=None, hsn='94036000', partner=None):
        move = self.init_invoice('out_invoice', partner=partner or self.partner_foreign, amounts=[1000.0],
                                 taxes=taxes, invoice_date=invoice_date or self.today)
        move.invoice_line_ids.write({'l10n_in_hsn_code': hsn})
        move.action_post()
        return move

    def _lut(self, invoice_date=None):
        fy = self.env['rn.gst.filing.period'].current_financial_year(invoice_date or self.today)
        return self.env['rn.gst.lut'].create({'financial_year': fy, 'arn': 'AD240425001234X'})

    def test_lut_needed(self):
        move = self._export(self.igst_sale_18_exp_lut)
        self.assertEqual(move.rn_exp_kind, 'lut')
        self.assertTrue(move.rn_exp_has_goods)
        self.assertEqual(move.rn_exp_check_state, 'error')
        self.assertIn('No LUT in force', move.rn_exp_check_messages)

        lut = self._lut()
        self.assertEqual(move.rn_exp_lut_id, lut)
        self.assertEqual(lut.invoice_count, 1)
        # Shipping bill not filled yet: only a warning within the 3 months.
        self.assertEqual(move.rn_exp_check_state, 'warning')
        self.assertIn('shipping bill number', move.rn_exp_check_messages)

        move.write({'l10n_in_shipping_bill_number': '1234567', 'l10n_in_shipping_bill_date': self.today,
                    'l10n_in_shipping_port_code_id': self.port.id})
        self.assertEqual(move.rn_exp_check_state, 'ok')

        lut.active = False
        self.assertFalse(move.rn_exp_lut_id)
        self.assertEqual(move.rn_exp_check_state, 'error')

    def test_goods_three_month_limit(self):
        old_date = self.today - relativedelta(months=4)
        self._lut(old_date)
        move = self._export(self.igst_sale_18_exp_lut, invoice_date=old_date)
        self.assertEqual(move.rn_exp_check_state, 'error')
        self.assertIn('within 3 months', move.rn_exp_check_messages)

        move.write({'l10n_in_shipping_bill_number': '1234567', 'l10n_in_shipping_port_code_id': self.port.id,
                    'l10n_in_shipping_bill_date': old_date + relativedelta(months=3, days=5)})
        self.assertEqual(move.rn_exp_check_state, 'error')
        self.assertIn('more than 3 months after', move.rn_exp_check_messages)
        move.l10n_in_shipping_bill_date = old_date + relativedelta(months=2)
        self.assertEqual(move.rn_exp_check_state, 'ok')

    def test_services_one_year_limit(self):
        old_date = self.today - relativedelta(months=13)
        self._lut(old_date)
        move = self._export(self.igst_sale_18_exp_lut, invoice_date=old_date, hsn='998314')
        self.assertFalse(move.rn_exp_has_goods)
        self.assertEqual(move.rn_exp_check_state, 'error')
        self.assertIn('not paid within one year', move.rn_exp_check_messages)
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=move.ids,
        ).create({'payment_date': self.today})._create_payments()
        self.assertEqual(move.rn_exp_check_state, 'ok')
        self.assertEqual(move.rn_exp_realised_amount, move.amount_total)
        self.assertEqual(move.rn_exp_realised_date, self.today)

    def test_igst_paid_refund_ready(self):
        move = self._export(self.igst_sale_18_exp)
        self.assertEqual(move.rn_exp_kind, 'igst')
        self.assertFalse(move.rn_exp_lut_id)
        self.assertFalse(move.rn_exp_refund_ready)
        move.write({'l10n_in_shipping_bill_number': '7654321', 'l10n_in_shipping_bill_date': self.today,
                    'l10n_in_shipping_port_code_id': self.port.id})
        self.assertTrue(move.rn_exp_refund_ready)
        self.assertEqual(move.rn_exp_check_state, 'ok')

    def test_mixed_lines(self):
        move = self.init_invoice('out_invoice', partner=self.partner_foreign, amounts=[1000.0, 500.0],
                                 invoice_date=self.today)
        move.invoice_line_ids[0].tax_ids = self.igst_sale_18_exp_lut
        move.invoice_line_ids[1].tax_ids = self.igst_sale_18_exp
        self.assertEqual(move.rn_exp_kind, 'mixed')
        self.assertIn('mixes LUT lines', move.rn_exp_check_messages)

    def test_sez_under_lut(self):
        move = self._export(self.igst_sale_18_sez_lut, partner=self.sez_partner)
        self.assertEqual(move.l10n_in_gst_treatment, 'special_economic_zone')
        self.assertEqual(move.rn_exp_kind, 'lut')
        self.assertIn('No LUT in force', move.rn_exp_check_messages)
        self._lut()
        # No shipping bill for SEZ supplies.
        self.assertEqual(move.rn_exp_check_state, 'ok')

    def test_domestic_invoice_ignored(self):
        move = self._export(self.sgst_sale_18, partner=self.partner_a)
        self.assertFalse(move.rn_exp_kind)
        self.assertFalse(move.rn_exp_check_state)
