# -*- coding: utf-8 -*-
import io

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes
from .common import RnGstFilingTestCommon

try:
    from openpyxl import Workbook, load_workbook
except ImportError:
    Workbook = None
    load_workbook = None


@tagged('post_install', '-at_install')
class TestRnGstExcel(RnGstFilingTestCommon):

    def _make_template_xlsx(self):
        wb = Workbook()
        default = wb.active
        wb.remove(default)
        sheets = {
            'b2b': ['GSTIN/UIN of Recipient', 'Receiver Name', 'Invoice Number', 'Invoice date', 'Invoice Value',
                    'Place Of Supply', 'Reverse Charge', 'Invoice Type', 'Rate', 'Taxable Value',
                    'Integrated Tax Paid', 'Central Tax Paid', 'State/UT Tax Paid', 'Cess Paid'],
            'b2cl': ['Invoice Number', 'Invoice date', 'Invoice Value', 'Place Of Supply', 'Rate', 'Taxable Value',
                     'Integrated Tax Paid', 'Cess Paid'],
            'b2cs': ['Type', 'Place Of Supply', 'Rate', 'Taxable Value', 'Integrated Tax Paid', 'Central Tax Paid',
                     'State/UT Tax Paid', 'Cess Paid'],
            'exp': ['Export Type', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Port Code',
                    'Shipping Bill Number', 'Shipping Bill Date', 'Rate', 'Taxable Value', 'Integrated Tax Paid'],
            'cdnr': ['GSTIN/UIN of Recipient', 'Receiver Name', 'Note Number', 'Note Date', 'Note Type',
                     'Place Of Supply', 'Reverse Charge', 'Note Value', 'Rate', 'Taxable Value',
                     'Integrated Tax Paid', 'Central Tax Paid', 'State/UT Tax Paid', 'Cess Paid'],
            'cdnur': ['UR Type', 'Note Number', 'Note Date', 'Note Type', 'Place Of Supply', 'Note Value',
                      'Rate', 'Taxable Value', 'Integrated Tax Paid', 'Cess Paid'],
            'hsn': ['HSN', 'Description', 'UQC', 'Total Quantity', 'Rate', 'Taxable Value',
                    'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount'],
            'nil': ['Description', 'Nil Rated Supplies', 'Exempted', 'Non-GST Supplies'],
            'docs': ['Nature of Document', 'Sr. No. From', 'Sr. No. To', 'Total Number', 'Cancelled'],
        }
        for name, headers in sheets.items():
            ws = wb.create_sheet(name)
            for col, header in enumerate(headers, start=1):
                ws.cell(row=1, column=col, value=header)
        buffer = io.BytesIO()
        wb.save(buffer)
        return BinaryBytes(buffer.getvalue())

    def test_template_inspect_and_generate(self):
        if Workbook is None:
            self.skipTest('openpyxl not installed')
        company = self.default_company
        company.rn_gst_recon_tolerance = 999999
        template = self.env['rn.gst.excel.template'].create({
            'name': 'Test GSTR-1 Template',
            'filing_type': 'gstr1',
            'version': '1',
            'financial_year': '2025-26',
            'company_id': company.id,
            'template_file': self._make_template_xlsx(),
            'template_filename': 'gstr1_test.xlsx',
        })
        template.action_inspect_workbook()
        self.assertTrue(template.mapping_json)
        self.assertIn('b2b', template.sheet_names)

        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-12',
        )
        filing = self._create_gst_filing('04')
        filing.template_id = template.id
        filing.action_load_data()
        filing.action_validate()
        if filing.validation_error_count:
            with self.assertRaises(UserError):
                filing.action_generate_excel()
            return
        filing.action_generate_excel()
        self.assertTrue(filing.generated_file)
        self.assertEqual(filing.state, 'generated')
        self.assertTrue(
            (filing.generated_filename or '').startswith('GSTR1_'),
            filing.generated_filename,
        )
        self.assertIn(filing.gstin or 'GSTIN', filing.generated_filename or '')
        wb = load_workbook(filename=io.BytesIO(filing.generated_file.content))
        self.assertIn('b2b', wb.sheetnames)
        b2b = wb['b2b']
        if b2b['A2'].value:
            self.assertIsInstance(b2b['A2'].value, str)

    def test_guess_logical_section_cdnur_not_cdnr(self):
        Template = self.env['rn.gst.excel.template']
        self.assertEqual(Template._guess_logical_section('cdnur', []), 'cdnur')
        self.assertEqual(Template._guess_logical_section('cdnr', []), 'cdnr')
        self.assertEqual(Template._guess_logical_section('exemp', []), 'nil')
        self.assertEqual(Template._guess_logical_section('b2cl', []), 'b2cl')
        self.assertEqual(Template._guess_logical_section('hsnb2b', []), 'hsn_b2b')
        self.assertEqual(Template._guess_logical_section('hsnb2c', []), 'hsn_b2c')
        self.assertFalse(Template._guess_logical_section('b2ba', []))
        self.assertFalse(Template._guess_logical_section('cdnra', []))

    def test_export_type_formatting(self):
        Generator = self.env['rn.gst.excel.generator']
        self.assertEqual(Generator._format_export_type('wpay'), 'WPAY')
        self.assertEqual(Generator._format_export_type('wopay'), 'WOPAY')

    def test_b2b_mixed_rate_rows(self):
        """Offline Tool B2B sheet needs one row per invoice rate, not one per invoice."""
        if Workbook is None:
            self.skipTest('openpyxl not installed')
        Generator = self.env['rn.gst.excel.generator']
        filing = self._create_gst_filing('04')
        Line = self.env['rn.gst.filing.line']
        common = {
            'filing_id': filing.id,
            'partner_id': self.partner_a.id,
            'partner_gstin': self.valid_partner_gstin_gj,
            'partner_name': self.partner_a.name,
            'invoice_number': 'INV/MIX/001',
            'invoice_date': '2025-04-15',
            'document_type': 'invoice',
            'place_of_supply_code': '24',
            'supply_type': 'b2b',
            'gst_table': 'b2b',
            'hsn_code': '998314',
            'invoice_value': 1230.0,
        }
        Line.create([
            dict(common, taxable_value=1000.0, gst_rate=18.0, cgst_amount=90.0, sgst_amount=90.0, igst_amount=0.0, cess_amount=0.0, total_tax=180.0),
            dict(common, taxable_value=500.0, gst_rate=5.0, cgst_amount=12.5, sgst_amount=12.5, igst_amount=0.0, cess_amount=0.0, total_tax=25.0),
        ])
        buckets = Generator._invoice_rate_buckets(filing.line_ids)
        self.assertEqual(len(buckets), 2)
        rates = sorted(b['rate'] for b in buckets.values())
        self.assertEqual(rates, [5.0, 18.0])
        taxable = {Generator._rate_key(b['rate']): b['taxable'] for b in buckets.values()}
        self.assertEqual(taxable[5.0], 500.0)
        self.assertEqual(taxable[18.0], 1000.0)

    def test_validation_hints_and_open_invoice(self):
        self.product_a.l10n_in_hsn_code = False
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-12',
        )
        self.default_company.rn_gst_recon_tolerance = 999999
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        filing.action_validate()
        issue = filing.validation_result_ids.filtered(lambda r: r.error_type == 'missing_hsn')[:1]
        self.assertTrue(issue)
        self.assertTrue(issue.hint)
        self.assertEqual(issue.move_id, move)
        action = issue.action_open_invoice()
        self.assertEqual(action['res_model'], 'account.move')
        self.assertEqual(action['res_id'], move.id)
