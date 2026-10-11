# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstMultiGstin(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_multi_gstin.group_rn_gst_multi_gstin_manager').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        # The GSTINs of the l10n_in test data fail the checksum; registrations need valid ones.
        cls.default_company.vat = '24AAGCC7144L6ZD'
        Registration = cls.env['rn.gst.registration']
        cls.reg_gj = Registration.create({
            'registration_name': 'Gujarat HO',
            'company_id': cls.default_company.id,
            'gstin': cls.default_company.vat,
            'is_default': True,
        })
        cls.reg_mh = Registration.create({
            'registration_name': 'Mumbai branch',
            'company_id': cls.default_company.id,
            'gstin': '27DJMPM8965E1ZJ',
        })
        cls.journal_mh = cls.env['account.journal'].create({
            'name': 'Sales Mumbai',
            'code': 'SMUM',
            'type': 'sale',
            'company_id': cls.default_company.id,
            'rn_gst_registration_id': cls.reg_mh.id,
        })
        cls.igst_purchase_18 = cls.env['account.chart.template'].ref('igst_purchase_18')

    def _invoice(self, partner, taxes, journal=None, move_type='out_invoice', date='2025-04-10'):
        move = self.init_invoice(move_type, partner=partner, amounts=[1000.0], taxes=taxes,
                                 invoice_date=date, journal=journal)
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        return move

    def test_registration_from_journal_or_default(self):
        default_invoice = self._invoice(self.partner_a, self.sgst_sale_18)
        self.assertEqual(default_invoice.rn_gst_registration_id, self.reg_gj)
        branch_invoice = self._invoice(self.partner_b, self.sgst_sale_18, journal=self.journal_mh)
        self.assertEqual(branch_invoice.rn_gst_registration_id, self.reg_mh)
        self.assertEqual(self.reg_mh.invoice_count, 1)
        self.assertEqual(self.reg_mh.journal_count, 1)

    def test_existing_documents_get_registration(self):
        old_invoice = self._invoice(self.partner_a, self.sgst_sale_18)
        old_invoice.action_post()
        old_invoice.rn_gst_registration_id = False
        journal = self.env['account.journal'].create({
            'name': 'Sales Pune', 'code': 'SPUN', 'type': 'sale', 'company_id': self.default_company.id,
        })
        pune_invoice = self._invoice(self.partner_b, self.igst_sale_18, journal=journal)
        pune_invoice.rn_gst_registration_id = False

        # Linking the journal fills its empty invoices only.
        journal.rn_gst_registration_id = self.reg_mh
        self.assertEqual(pune_invoice.rn_gst_registration_id, self.reg_mh)
        self.assertFalse(old_invoice.rn_gst_registration_id)

        # Marking a registration default fills the rest, but never changes a filled one.
        self.reg_gj.is_default = False
        self.reg_gj.is_default = True
        self.assertEqual(old_invoice.rn_gst_registration_id, self.reg_gj)
        self.assertEqual(pune_invoice.rn_gst_registration_id, self.reg_mh)

    def test_only_one_default(self):
        with self.assertRaises(ValidationError):
            self.reg_mh.is_default = True

    def test_supply_type_follows_registration_state(self):
        # Mumbai customer billed from the Mumbai GSTIN: intra-state, CGST/SGST is right.
        branch = self._invoice(self.partner_b, self.sgst_sale_18, journal=self.journal_mh)
        self.assertEqual(branch.rn_gst_supply_type, 'intra')
        self.assertFalse(branch.rn_gst_tax_mismatch)

        # Same customer billed from the Gujarat GSTIN with CGST/SGST: wrong, should be IGST.
        wrong = self._invoice(self.partner_b, self.sgst_sale_18)
        self.assertEqual(wrong.rn_gst_supply_type, 'inter')
        self.assertTrue(wrong.rn_gst_tax_mismatch)
        self.assertIn('IGST', wrong.rn_gst_tax_warning)
        self.assertIn(wrong, self.env['account.move'].search([('rn_gst_tax_mismatch', '=', True)]))

        wrong.invoice_line_ids.tax_ids = self.igst_sale_18
        self.assertFalse(wrong.rn_gst_tax_mismatch)

        # IGST inside Gujarat is wrong too.
        intra_igst = self._invoice(self.partner_a, self.igst_sale_18)
        self.assertEqual(intra_igst.rn_gst_supply_type, 'intra')
        self.assertTrue(intra_igst.rn_gst_tax_mismatch)

    def test_purchase_uses_supplier_gstin_state(self):
        bill = self._invoice(self.partner_b, self.igst_purchase_18, move_type='in_invoice')
        self.assertEqual(bill.rn_gst_registration_id, self.reg_gj)
        self.assertEqual(bill.rn_gst_supply_type, 'inter')
        self.assertFalse(bill.rn_gst_tax_mismatch)
        local_bill = self._invoice(self.partner_a, self.igst_purchase_18, move_type='in_invoice')
        self.assertTrue(local_bill.rn_gst_tax_mismatch)

    def test_post_outside_effective_dates(self):
        self.reg_mh.write({'effective_from': '2025-01-01', 'effective_to': '2025-03-31'})
        late = self._invoice(self.partner_b, self.sgst_sale_18, journal=self.journal_mh, date='2025-04-10')
        with self.assertRaises(UserError):
            late.action_post()
        on_time = self._invoice(self.partner_b, self.sgst_sale_18, journal=self.journal_mh, date='2025-03-10')
        on_time.action_post()
        self.assertEqual(on_time.state, 'posted')

    def test_post_archived_registration(self):
        invoice = self._invoice(self.partner_b, self.sgst_sale_18, journal=self.journal_mh)
        self.reg_mh.active = False
        with self.assertRaises(UserError):
            invoice.action_post()
