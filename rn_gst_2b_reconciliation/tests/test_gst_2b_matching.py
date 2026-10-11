# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGst2bMatching(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref(
            'rn_gst_2b_reconciliation.group_rn_gst_2b_manager'
        ).id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.default_company.rn_gst_2b_amount_tolerance = 1.0
        cls.default_company.rn_gst_2b_date_tolerance_days = 3
        cls.vendor_gstin = '24AAPFU0939F1Z1'
        cls.partner_a.vat = cls.vendor_gstin
        cls.partner_a.l10n_in_gst_treatment = 'regular'
        cls.product_a.l10n_in_hsn_code = '998314'

    def _make_posted_bill(self, amount, invoice_date, ref=None, taxes=None):
        bill = self.init_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            amounts=[amount],
            taxes=taxes or self.sgst_purchase_5,
            post=False,
            invoice_date=invoice_date,
        )
        bill.invoice_line_ids.filtered(
            lambda l: l.display_type in (False, 'product')
        ).write({'l10n_in_hsn_code': '998314'})
        if ref:
            bill.ref = ref
        bill.action_post()
        return bill

    def _create_reconciliation(self, period='04'):
        start, end = self.env['rn.gst.filing.period'].compute_period_dates('2025-26', period, 'monthly')
        return self.env['rn.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': period,
            'filing_frequency': 'monthly',
            'period_start': start,
            'period_end': end,
        })

    def _import_csv(self, reconciliation, csv_text):
        wizard = self.env['rn.gst.2b.import.wizard'].create({
            'reconciliation_id': reconciliation.id,
            'data_file': BinaryBytes(csv_text.encode('utf-8')),
            'filename': 'gstr2b.csv',
            'replace_existing': True,
        })
        wizard.action_import()
        return reconciliation

    def test_matched_bill(self):
        bill = self._make_posted_bill(
            amount=1000.0,
            invoice_date='2025-04-15',
            ref='BILL-2B-001',
        )

        csv = (
            'GSTIN,Invoice Number,Invoice Date,Taxable Value,CGST,SGST,IGST,Cess,Invoice Value,Vendor Name\n'
            '%s,BILL-2B-001,15-04-2025,1000,25,25,0,0,1050,Test Vendor\n'
        ) % self.vendor_gstin
        recon = self._create_reconciliation()
        self._import_csv(recon, csv)
        recon.action_run_matching()

        line = recon.line_ids.filtered(lambda l: l.source == 'gstr2b')[:1]
        self.assertEqual(line.match_state, 'matched')
        self.assertEqual(line.move_id, bill)
        self.assertGreater(recon.count_matched, 0)

    def test_missing_in_odoo(self):
        csv = (
            'GSTIN,Invoice Number,Invoice Date,Taxable Value,CGST,SGST,IGST,Cess\n'
            '%s,ONLY-2B-999,10-04-2025,500,0,45,0,0\n'
        ) % self.vendor_gstin
        recon = self._create_reconciliation()
        self._import_csv(recon, csv)
        recon.action_run_matching()

        line = recon.line_ids.filtered(lambda l: l.invoice_number == 'ONLY-2B-999')
        self.assertEqual(line.match_state, 'missing_in_odoo')
        self.assertEqual(recon.count_missing_odoo, 1)

    def test_missing_in_2b(self):
        bill = self._make_posted_bill(
            amount=800.0,
            invoice_date='2025-04-12',
            ref='ONLY-ODOO-888',
        )

        csv = (
            'GSTIN,Invoice Number,Invoice Date,Taxable Value,CGST,SGST,IGST,Cess\n'
            '%s,OTHER-2B-001,10-04-2025,100,0,5,0,0\n'
        ) % self.vendor_gstin
        recon = self._create_reconciliation()
        self._import_csv(recon, csv)
        recon.action_run_matching()

        gap = recon.line_ids.filtered(lambda l: l.source == 'odoo')
        self.assertTrue(gap)
        self.assertEqual(gap[:1].match_state, 'missing_in_2b')
        self.assertEqual(recon.count_missing_2b, 1)

    def test_create_vendor_bill_from_2b(self):
        csv = (
            'GSTIN,Invoice Number,Invoice Date,Taxable Value,CGST,SGST,IGST,Cess\n'
            '%s,NEW-2B-777,20-04-2025,2000,0,180,0,0\n'
        ) % self.vendor_gstin
        recon = self._create_reconciliation()
        self._import_csv(recon, csv)
        recon.action_run_matching()
        line = recon.line_ids.filtered(lambda l: l.invoice_number == 'NEW-2B-777')
        self.assertEqual(line.match_state, 'missing_in_odoo')

        action = line.action_create_vendor_bill()
        self.assertTrue(line.move_id)
        self.assertEqual(action['res_model'], 'account.move')
        self.assertEqual(line.move_id.ref, 'NEW-2B-777')

    def test_mismatch_amount(self):
        bill = self._make_posted_bill(
            amount=1000.0,
            invoice_date='2025-04-18',
            ref='MISMATCH-001',
        )

        csv = (
            'GSTIN,Invoice Number,Invoice Date,Taxable Value,CGST,SGST,IGST,Cess\n'
            '%s,MISMATCH-001,18-04-2025,1000,0,200,0,0\n'
        ) % self.vendor_gstin
        recon = self._create_reconciliation()
        self._import_csv(recon, csv)
        recon.action_run_matching()

        line = recon.line_ids.filtered(lambda l: l.invoice_number == 'MISMATCH-001')
        self.assertEqual(line.match_state, 'mismatch')
        self.assertTrue(line.mismatch_detail)

    def test_reverse_charge_bill_tax_counted_once(self):
        tax = self.env.ref('account.%s_igst_purchase_18_rc' % self.default_company.id)
        if 'rn_gst_block_post_on_error' in self.default_company._fields:
            # Invoice Validator (when installed) checks IGST vs place of supply, not under test here.
            self.default_company.rn_gst_block_post_on_error = False
        bill =self._make_posted_bill(1000.0, '2025-04-10', ref='RC-001', taxes=tax)
        amounts = self.env['rn.gst.2b.matching']._bill_tax_amounts(bill)
        self.assertAlmostEqual(amounts['igst_amount'], 180.0, places=2)
