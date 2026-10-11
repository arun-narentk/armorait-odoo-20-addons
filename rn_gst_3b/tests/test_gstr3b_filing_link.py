# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.rn_gst_filing.tests.common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGst3bFilingLink(RnGstFilingTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_base.group_rn_gst_administrator').id)]

    def test_create_gstr3b_from_gstr1_filing(self):
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-12',
        )
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        action = filing.action_create_gstr3b()
        self.assertEqual(action['res_model'], 'rn.gst.3b')
        gstr3b = self.env['rn.gst.3b'].browse(action['res_id'])
        self.assertEqual(gstr3b.return_period, '04')
        self.assertEqual(gstr3b.liability_cgst, filing.amount_cgst)
        self.assertEqual(filing.gstr3b_id, gstr3b)

    def test_wizard_gstr3b_redirect(self):
        wizard = self.env['rn.gst.filing.generate.wizard'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_type': 'gstr3b',
            'filing_frequency': 'monthly',
        })
        action = wizard.action_create_and_load()
        self.assertEqual(action['res_model'], 'rn.gst.3b')
        gstr3b = self.env['rn.gst.3b'].browse(action['res_id'])
        self.assertTrue(gstr3b.exists())
