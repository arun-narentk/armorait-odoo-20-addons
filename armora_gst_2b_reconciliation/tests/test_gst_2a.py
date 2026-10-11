# -*- coding: utf-8 -*-
import io

from openpyxl import Workbook

from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

B2B_HEADER = [
    ['GSTIN of supplier', 'Trade/Legal name of the Supplier', 'Invoice details', None, None, None,
     'Place of supply', 'Supply Attract Reverse Charge', 'Rate (%)', 'Taxable Value (₹)',
     'Tax Amount', None, None, None,
     'GSTR-1/IFF/GSTR-5 Filing Status', 'GSTR-1/IFF/GSTR-5 Filing Date', 'GSTR-1/IFF/GSTR-5 Filing Period',
     'GSTR-3B Filing Status'],
    [None, None, 'Invoice number', 'Invoice type', 'Invoice Date', 'Invoice Value (₹)',
     None, None, None, None, 'Integrated Tax (₹)', 'Central Tax (₹)', 'State/UT tax (₹)', 'Cess (₹)',
     None, None, None, None],
]
CDNR_HEADER = [
    ['GSTIN of supplier', 'Trade/Legal name of the Supplier', 'Credit note/Debit note details', None, None, None,
     'Place of supply', 'Supply Attract Reverse Charge', 'Rate (%)', 'Taxable Value (₹)',
     'Tax Amount', None, None, None,
     'GSTR-1/IFF/GSTR-5 Filing Status', 'GSTR-1/IFF/GSTR-5 Filing Date', 'GSTR-1/IFF/GSTR-5 Filing Period',
     'GSTR-3B Filing Status'],
    [None, None, 'Note number', 'Note type', 'Note date', 'Note Value (₹)',
     None, None, None, None, 'Integrated Tax (₹)', 'Central Tax (₹)', 'State/UT tax (₹)', 'Cess (₹)',
     None, None, None, None],
]


@tagged('post_install', '-at_install')
class TestArmoraGst2a(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref(
            'armora_gst_2b_reconciliation.group_armora_gst_2b_manager'
        ).id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.vendor_gstin = '24AAPFU0939F1Z1'
        cls.partner_a.write({'vat': cls.vendor_gstin, 'l10n_in_gst_treatment': 'regular'})

    def _portal_workbook(self):
        """A workbook laid out like the GSTR-2A download: title rows, a two-row header,
        one row per tax rate, and the supplier filing columns."""
        book = Workbook()
        readme = book.active
        readme.title = 'Read me'
        readme.append(['Goods and Services Tax - GSTR-2A'])
        b2b = book.create_sheet('B2B')
        b2b.append(['Taxpayer-wise details of supplies'])
        b2b.append([])
        for row in B2B_HEADER:
            b2b.append(row)
        g = self.vendor_gstin
        # INV-2A-1 has two rate rows; together they equal the vendor bill.
        b2b.append([g, 'Test Vendor', 'INV-2A-1', 'Regular', '15-04-2025', 1575, 'Gujarat', 'N', 5, 1000, 0, 25, 25, 0, 'Y', '11-05-2025', 'Apr-25', 'Y'])
        b2b.append([g, 'Test Vendor', 'INV-2A-1', 'Regular', '15-04-2025', 1575, 'Gujarat', 'N', 5, 500, 0, 12.5, 12.5, 0, 'Y', '11-05-2025', 'Apr-25', 'Y'])
        b2b.append([g, 'Test Vendor', 'INV-2A-2', 'Regular', '20-04-2025', 1050, 'Gujarat', 'N', 5, 1000, 0, 25, 25, 0, 'Y', '11-05-2025', 'Apr-25', 'N'])
        cdnr = book.create_sheet('CDNR')
        for row in CDNR_HEADER:
            cdnr.append(row)
        cdnr.append([g, 'Test Vendor', 'CN-2A-1', 'Credit Note', '25-04-2025', 105, 'Gujarat', 'N', 5, 100, 0, 2.5, 2.5, 0, 'Y', '11-05-2025', 'Apr-25', 'Y'])
        output = io.BytesIO()
        book.save(output)
        return output.getvalue()

    def _create_reconciliation(self, statement_type):
        return self.env['armora.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'statement_type': statement_type,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'period_start': '2025-04-01',
            'period_end': '2025-04-30',
        })

    def test_gstr2a_import_and_match(self):
        bill = self.init_invoice(
            move_type='in_invoice', partner=self.partner_a, amounts=[1000.0, 500.0],
            taxes=self.sgst_purchase_5, invoice_date='2025-04-15',
        )
        bill.ref = 'INV-2A-1'
        bill.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        bill.action_post()

        recon = self._create_reconciliation('gstr2a')
        # A GSTR-2B of the same month can exist next to the GSTR-2A.
        self._create_reconciliation('gstr2b')
        self.env['armora.gst.2b.import.wizard'].create({
            'reconciliation_id': recon.id,
            'data_file': BinaryBytes(self._portal_workbook()),
            'filename': 'gstr2a_apr_2025.xlsx',
        }).action_import()

        portal = recon.line_ids.filtered(lambda l: l.source == 'gstr2b')
        self.assertEqual(len(portal), 3, 'Two rate rows of INV-2A-1 are one line; the credit note is read too.')
        inv1 = portal.filtered(lambda l: l.invoice_number == 'INV-2A-1')
        self.assertAlmostEqual(inv1.taxable_value, 1500.0)
        self.assertAlmostEqual(inv1.cgst_amount, 37.5)
        self.assertAlmostEqual(inv1.invoice_value, 1575.0)
        self.assertEqual(inv1.supplier_filing_status, 'filed')
        self.assertEqual(str(inv1.supplier_filing_date), '2025-05-11')
        self.assertEqual(inv1.supplier_filing_period, 'Apr-25')
        inv2 = portal.filtered(lambda l: l.invoice_number == 'INV-2A-2')
        self.assertEqual(inv2.supplier_3b_status, 'not_filed')
        note = portal.filtered(lambda l: l.invoice_number == 'CN-2A-1')
        self.assertEqual(note.document_type, 'credit_note')

        recon.action_run_matching()
        self.assertEqual(inv1.match_state, 'matched')
        self.assertEqual(inv1.move_id, bill)
        self.assertEqual(inv2.match_state, 'missing_in_odoo')
        at_risk = self.env['armora.gst.gstr2b.line'].search([
            ('reconciliation_id', '=', recon.id), ('supplier_3b_status', '=', 'not_filed'),
        ])
        self.assertEqual(at_risk, inv2)

        action = recon.action_export_excel()
        self.assertIn('GSTR-2A', self.env['ir.attachment'].search([
            ('res_model', '=', 'armora.gst.gstr2b'), ('res_id', '=', recon.id),
        ]).name)
        self.assertEqual(action['type'], 'ir.actions.act_url')

    def test_period_dates_without_frequency(self):
        recon = self.env['armora.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'statement_type': 'gstr2a',
            'financial_year': '2025-26',
            'return_period': '05',
        })
        self.assertEqual((str(recon.period_start), str(recon.period_end)), ('2025-05-01', '2025-05-31'))
        self.assertEqual(recon.gstin, self.default_company.vat)
        self.assertTrue(recon.name.startswith('2A/'))
