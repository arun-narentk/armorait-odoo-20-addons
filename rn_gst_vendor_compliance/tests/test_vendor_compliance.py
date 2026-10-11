# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstVendorCompliance(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_vendor_compliance.group_rn_gst_vendor_compliance_manager').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.today = fields.Date.today()
        cls.Profile = cls.env['rn.gst.vendor.profile']
        cls.supplier = cls.env['res.partner'].create({
            'name': 'Good Supplier', 'is_company': True, 'vat': '27DJMPM8965E1ZJ',
            'country_id': cls.country_in.id, 'state_id': cls.state_in_mh.id, 'l10n_in_gst_treatment': 'regular',
        })

    def _bill(self, partner, taxes=None, post=True):
        bill = self.init_invoice('in_invoice', partner=partner, amounts=[10000.0],
                                 taxes=taxes if taxes is not None else self.sgst_purchase_5,
                                 invoice_date=self.today - relativedelta(days=10))
        bill.invoice_line_ids.write({'l10n_in_hsn_code': '94036000'})
        if post:
            bill.action_post()
        return bill

    def _profile(self, partner):
        profile = self.Profile.create({'partner_id': partner.id})
        profile.action_refresh()
        return profile

    def test_good_supplier(self):
        self._bill(self.supplier)
        profile = self._profile(self.supplier)
        self.assertEqual(profile.bill_count, 1)
        self.assertEqual(profile.bill_amount, 10000.0)
        self.assertIn(profile.gstin_status, ('structure_ok', 'unknown'))
        self.assertEqual(profile.risk, 'low')
        self.assertEqual(profile.decision, 'allow')
        self.assertIn('gstin_not_verified', profile.finding_ids.mapped('code'))

    def test_no_bills_is_unknown(self):
        profile = self._profile(self.supplier)
        self.assertEqual(profile.risk, 'unknown')
        self.assertEqual(profile.decision, 'allow')

    def test_composition_supplier_charging_gst(self):
        self.supplier.l10n_in_gst_treatment = 'composition'
        self._bill(self.supplier)
        profile = self._profile(self.supplier)
        self.assertIn('composition_tax', profile.finding_ids.mapped('code'))
        self.assertEqual(profile.risk, 'medium')
        self.assertEqual(profile.decision, 'warn')

    def test_invalid_gstin_blocks(self):
        self.supplier.vat = '27DJMPM8965E1ZE'
        draft = self._bill(self.supplier, post=False)
        profile = self._profile(self.supplier)
        self.assertEqual(profile.gstin_status, 'invalid')
        self.assertEqual(profile.decision, 'block')
        self.assertEqual(draft.rn_vendor_decision, 'block')
        self.assertIn('Block', draft.rn_vendor_warning)

        self.default_company.rn_vendor_block_posting = True
        with self.assertRaises(UserError):
            draft.action_post()

        with self.assertRaises(UserError):
            profile.decision_override = 'allow'
        profile.write({'decision_override': 'allow', 'override_reason': 'GSTIN corrected on paper, Odoo update pending'})
        self.assertEqual(profile.decision, 'allow')
        draft.invalidate_recordset(['rn_vendor_decision'])
        draft.action_post()
        self.assertEqual(draft.state, 'posted')

    def test_not_in_gstr2b(self):
        if 'rn.gst.gstr2b.line' not in self.env:
            self.skipTest('Armora GSTR-2B Reconciliation is not installed.')
        bill = self._bill(self.supplier)
        start = self.today.replace(day=1)
        recon = self.env['rn.gst.gstr2b'].sudo().create({
            'company_id': self.default_company.id, 'gstin': self.default_company.vat,
            'financial_year': self.env['rn.gst.filing.period'].current_financial_year(self.today),
            'return_period': '%02d' % self.today.month, 'period_start': start,
            'period_end': start + relativedelta(months=1, days=-1),
        })
        self.env['rn.gst.gstr2b.line'].sudo().create({
            'reconciliation_id': recon.id, 'source': 'odoo', 'partner_id': self.supplier.id,
            'move_id': bill.id, 'invoice_date': bill.invoice_date, 'invoice_number': 'S-1',
            'cgst_amount': 250.0, 'sgst_amount': 250.0, 'match_state': 'missing_in_2b',
        })
        profile = self._profile(self.supplier)
        self.assertEqual(profile.missing_2b_count, 1)
        self.assertEqual(profile.itc_at_risk, 500.0)
        self.assertIn('not_in_2b', profile.finding_ids.mapped('code'))

    def test_foreign_supplier(self):
        foreign = self.env['res.partner'].create({
            'name': 'Shenzhen Parts Co', 'is_company': True, 'country_id': self.env.ref('base.cn').id,
        })
        self._bill(foreign, taxes=self.env['account.tax'])
        profile = self._profile(foreign)
        self.assertEqual(profile.gstin_status, 'foreign')
        self.assertEqual(profile.decision, 'allow')

    def test_create_all(self):
        self._bill(self.supplier)
        self.Profile.action_create_all()
        self.assertTrue(self.Profile.search([('partner_id', '=', self.supplier.id)]))
