# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnEwaybillManager(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_company.l10n_in_ewaybill_feature = True
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.Ewaybill = cls.env['l10n.in.ewaybill']

    def _invoice(self, amount, hsn='94036000'):
        move = self.init_invoice('out_invoice', partner=self.partner_b, amounts=[amount], taxes=self.igst_sale_18,
                                 invoice_date=fields.Date.today())
        move.invoice_line_ids.write({'l10n_in_hsn_code': hsn})
        move.invoice_user_id = self.env.user
        move.action_post()
        return move

    def test_missing_ewaybill(self):
        goods = self._invoice(60000.0)
        self.assertTrue(goods.rn_ewb_missing)
        self.assertIn(goods, self.env['account.move'].search([('rn_ewb_missing', '=', True)]))
        self.assertFalse(self._invoice(60000.0, hsn='998314').rn_ewb_missing)
        self.assertFalse(self._invoice(30000.0).rn_ewb_missing)

        ewb = self.Ewaybill.create({'account_move_id': goods.id})
        self.assertFalse(goods.rn_ewb_missing)
        ewb.state = 'cancel'
        self.assertTrue(goods.rn_ewb_missing)

        self.default_company.rn_ewb_threshold = 100000.0
        self.assertFalse(goods.rn_ewb_missing)

    def test_vendor_bills(self):
        registered = self.init_invoice('in_invoice', partner=self.partner_b, amounts=[60000.0],
                                       invoice_date=fields.Date.today())
        registered.invoice_line_ids.write({'l10n_in_hsn_code': '94036000'})
        registered.action_post()
        self.assertFalse(registered.rn_ewb_missing)
        unregistered = self.env['res.partner'].create({'name': 'Local Scrap Dealer', 'country_id': self.country_in.id})
        bill = self.init_invoice('in_invoice', partner=unregistered, amounts=[60000.0],
                                 invoice_date=fields.Date.today())
        bill.invoice_line_ids.write({'l10n_in_hsn_code': '72044900'})
        bill.action_post()
        self.assertTrue(bill.rn_ewb_missing)

    def test_stages_and_validity(self):
        move = self._invoice(60000.0)
        ewb = self.Ewaybill.create({'account_move_id': move.id, 'distance': 450})
        self.assertEqual(ewb.rn_ewb_stage, 'to_generate')
        self.assertEqual(ewb.rn_ewb_partner_id, self.partner_b)
        self.assertEqual(ewb.rn_ewb_expected_days, 3)
        ewb.error_message = '<p>Invalid vehicle number</p>'
        self.assertEqual(ewb.rn_ewb_stage, 'failed')

        today = fields.Date.today()
        ewb.write({'error_message': False, 'state': 'generated', 'name': '331000000001',
                   'ewaybill_date': today, 'ewaybill_expiry_date': today + timedelta(days=1)})
        self.assertEqual(ewb.rn_ewb_stage, 'generated')
        self.assertTrue(ewb.rn_ewb_expiring)
        self.assertFalse(ewb.rn_ewb_expired)
        self.assertEqual(ewb.rn_ewb_days_left, 1)
        self.assertIn(ewb, self.Ewaybill.search([('rn_ewb_expiring', '=', True)]))

        ewb.ewaybill_expiry_date = today - timedelta(days=2)
        self.assertTrue(ewb.rn_ewb_expired)
        self.assertIn(ewb, self.Ewaybill.search([('rn_ewb_expired', '=', True)]))
        self.assertNotIn(ewb, self.Ewaybill.search([('rn_ewb_expiring', '=', True)]))

    def test_expiry_reminder(self):
        move = self._invoice(60000.0)
        today = fields.Date.today()
        ewb = self.Ewaybill.create({'account_move_id': move.id})
        ewb.write({'state': 'generated', 'name': '331000000002', 'ewaybill_date': today,
                   'ewaybill_expiry_date': today})
        self.Ewaybill._cron_rn_ewb_expiry()
        self.assertEqual(ewb.activity_ids.user_id, self.env.user)
        self.Ewaybill._cron_rn_ewb_expiry()
        self.assertEqual(len(ewb.activity_ids), 1)
