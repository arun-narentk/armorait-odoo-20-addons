# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstCustomerCompliance(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_customer_compliance.group_rn_gst_customer_compliance_user').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.today = fields.Date.today()
        cls.Profile = cls.env['rn.gst.customer.profile']
        cls.customer = cls.env['res.partner'].create({
            'name': 'Mumbai Retail Pvt Ltd', 'is_company': True, 'vat': '27DJMPM8965E1ZJ',
            'country_id': cls.country_in.id, 'state_id': cls.state_in_mh.id, 'l10n_in_gst_treatment': 'regular',
        })

    def _invoice(self, partner, amount=10000.0, move_type='out_invoice'):
        move = self.init_invoice(move_type, partner=partner, amounts=[amount], taxes=self.igst_sale_18,
                                 invoice_date=self.today - relativedelta(days=5))
        move.invoice_line_ids.write({'l10n_in_hsn_code': '94036000'})
        move.action_post()
        return move

    def _profile(self, partner):
        profile = self.Profile.create({'partner_id': partner.id})
        profile.action_refresh()
        return profile

    def test_clean_customer(self):
        self._invoice(self.customer)
        profile = self._profile(self.customer)
        self.assertEqual(profile.invoice_count, 1)
        self.assertEqual(profile.sales_amount, 10000.0)
        self.assertEqual(profile.risk, 'low')

    def test_b2b_set_up_as_consumer(self):
        self.customer.l10n_in_gst_treatment = 'consumer'
        self._invoice(self.customer)
        profile = self._profile(self.customer)
        self.assertIn('b2b_as_b2c', profile.finding_ids.mapped('code'))
        self.assertIn('Consumer', profile.finding_ids.filtered(lambda f: f.code == 'b2b_as_b2c').message)
        self.assertEqual(profile.risk, 'medium')

    def test_state_mismatch_and_invalid(self):
        self.customer.state_id = self.state_in_gj
        profile = self._profile(self.customer)
        self.assertIn('state_mismatch', profile.finding_ids.mapped('code'))
        self.customer.vat = '27DJMPM8965E1ZE'
        self._invoice(self.customer)
        profile.action_refresh()
        self.assertEqual(profile.gstin_status, 'invalid')
        self.assertEqual(profile.risk, 'high')
        draft = self.init_invoice('out_invoice', partner=self.customer, amounts=[100.0], invoice_date=self.today)
        self.assertIn('high', draft.rn_customer_warning)

    def test_credit_note_share(self):
        self._invoice(self.customer, 10000.0)
        self._invoice(self.customer, 3000.0, move_type='out_refund')
        profile = self._profile(self.customer)
        self.assertEqual(profile.credit_amount, 3000.0)
        self.assertIn('credit_note_share', profile.finding_ids.mapped('code'))

    def test_foreign_and_unknown(self):
        foreign = self.env['res.partner'].create({'name': 'Dubai Trading LLC', 'is_company': True,
                                                  'country_id': self.env.ref('base.ae').id})
        profile = self._profile(foreign)
        self.assertEqual(profile.gstin_status, 'foreign')
        self.assertEqual(profile.risk, 'unknown')

    def test_create_all(self):
        self._invoice(self.customer)
        self.Profile.action_create_all()
        self.assertTrue(self.Profile.search([('partner_id', '=', self.customer.id)]))
