# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from .common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGstFiling(RnGstFilingTestCommon):

    def test_snapshot_and_regenerate(self):
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-15',
        )
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        self.assertEqual(filing.state, 'data_loaded')
        self.assertTrue(filing.line_ids)
        self.assertTrue(filing.is_snapshot_locked)
        count1 = len(filing.line_ids)
        filing.action_regenerate_snapshot()
        self.assertEqual(filing.state, 'data_loaded')
        self.assertEqual(len(filing.line_ids), count1)

    def test_filed_readonly(self):
        filing = self._create_gst_filing('05')
        filing.state = 'filed'
        with self.assertRaises(UserError):
            filing.write({'notes': 'should fail'})

    def test_snapshot_locked_after_data_load(self):
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-15',
        )
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        self.assertEqual(filing.state, 'data_loaded')
        self.assertTrue(filing.is_snapshot_locked)
        line = filing.line_ids[:1]
        with self.assertRaises(UserError):
            line.write({'invoice_number': 'CHANGED'})

    def test_snapshot_locked_after_validate(self):
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-15',
        )
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        filing.action_validate()
        self.assertEqual(filing.state, 'validated')
        line = filing.line_ids[:1]
        with self.assertRaises(UserError):
            line.write({'invoice_number': 'CHANGED'})
        self.assertTrue(filing.is_snapshot_locked)

    def test_gst_registration_consistency(self):
        company = self.default_company
        registration = self.env['rn.gst.registration'].create({
            'registration_name': 'Main GSTIN',
            'company_id': company.id,
            'gstin': company.vat,
            'state_id': company.state_id.id,
            'state_code': company.state_id.l10n_in_tin or '24',
            'registration_type': 'regular',
        })
        filing = self._create_gst_filing('06')
        filing.gst_registration_id = registration.id
        self.assertEqual(filing.gstin, registration.gstin)
        with self.assertRaises(ValidationError):
            filing.write({'gstin': '27AAPFU0939F1ZV'})

    def test_security_groups_exist(self):
        self.assertTrue(self.env.ref('rn_gst_filing.group_rn_gst_filing_user'))
        self.assertTrue(self.env.ref('rn_gst_filing.group_rn_gst_filing_manager'))
        self.assertTrue(self.env.ref('rn_gst_filing.group_rn_gst_filing_administrator'))
