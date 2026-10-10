# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGst2bImport(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref(
            'armora_gst_2b_reconciliation.group_armora_gst_2b_manager'
        ).id)]
        cls.default_company.vat = '24AAACB6992P1Z3'

    def test_csv_import_maps_rows(self):
        start, end = self.env['armora.gst.period'].compute_period_dates('2025-26', '04', 'monthly')
        recon = self.env['armora.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_frequency': 'monthly',
            'period_start': start,
            'period_end': end,
        })
        csv = (
            'Supplier GSTIN,Invoice No,Invoice Date,Taxable Amount,Central Tax,State Tax\n'
            '24AAPFU0939F1Z1,IMP-001,01-04-2025,1500,135,135\n'
        )
        wizard = self.env['armora.gst.2b.import.wizard'].create({
            'reconciliation_id': recon.id,
            'data_file': BinaryBytes(csv.encode('utf-8')),
            'filename': 'test.csv',
        })
        wizard.action_import()
        self.assertEqual(recon.state, 'imported')
        line = recon.line_ids[:1]
        self.assertEqual(line.vendor_gstin, '24AAPFU0939F1Z1')
        self.assertEqual(line.invoice_number, 'IMP-001')
        self.assertAlmostEqual(line.taxable_value, 1500.0, places=2)
        self.assertAlmostEqual(line.cgst_amount, 135.0, places=2)
        self.assertAlmostEqual(line.sgst_amount, 135.0, places=2)

    def test_empty_file_raises(self):
        start, end = self.env['armora.gst.period'].compute_period_dates('2025-26', '04', 'monthly')
        recon = self.env['armora.gst.gstr2b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_frequency': 'monthly',
            'period_start': start,
            'period_end': end,
        })
        wizard = self.env['armora.gst.2b.import.wizard'].create({
            'reconciliation_id': recon.id,
            'data_file': BinaryBytes(b'GSTIN\n'),
            'filename': 'empty.csv',
        })
        with self.assertRaises(UserError):
            wizard.action_import()
