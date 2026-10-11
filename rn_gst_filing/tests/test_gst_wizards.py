# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from .common import RnGstFilingTestCommon, Workbook


@tagged('post_install', '-at_install')
class TestRnGstFilingWizards(RnGstFilingTestCommon):

    def test_generate_wizard_end_to_end(self):
        if Workbook is None:
            self.skipTest('openpyxl not installed')
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-12',
        )
        template = self.env['rn.gst.excel.template'].create({
            'name': 'Wizard Test Template',
            'filing_type': 'gstr1',
            'version': '1',
            'financial_year': '2025-26',
            'company_id': self.default_company.id,
            'template_file': self._make_template_xlsx(),
            'template_filename': 'gstr1_test.xlsx',
        })
        template.action_inspect_workbook()

        wizard = self.env['rn.gst.filing.generate.wizard'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_type': 'gstr1',
            'filing_frequency': 'monthly',
        })
        wizard.action_create_and_load()
        self.assertEqual(wizard.step, 'loaded')
        self.assertTrue(wizard.filing_id)
        self.assertTrue(wizard.filing_id.line_ids)
        self.assertGreater(wizard.document_count, 0)

        wizard.filing_id.template_id = template.id
        wizard.action_validate()
        self.assertEqual(wizard.step, 'validated')

        if wizard.validation_error_count:
            with self.assertRaises(UserError):
                wizard.action_generate_excel()
            return

        wizard.action_generate_excel()
        self.assertEqual(wizard.step, 'generated')
        self.assertTrue(wizard.filing_id.generated_file)

        action = wizard.action_open_filing()
        self.assertEqual(action['res_model'], 'rn.gst.filing')
        self.assertEqual(action['res_id'], wizard.filing_id.id)

    def test_generate_wizard_reuses_draft_filing(self):
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[500.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-04-10',
        )
        existing = self._create_gst_filing('04')
        wizard = self.env['rn.gst.filing.generate.wizard'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_type': 'gstr1',
            'filing_frequency': 'monthly',
        })
        wizard.action_create_and_load()
        self.assertEqual(wizard.filing_id, existing)

    def test_template_import_wizard(self):
        if Workbook is None:
            self.skipTest('openpyxl not installed')
        wizard = self.env['rn.gst.excel.template.import.wizard'].create({
            'name': 'Imported Offline Tool',
            'filing_type': 'gstr1',
            'version': '2025-26-v1',
            'financial_year': '2025-26',
            'company_id': self.default_company.id,
            'template_file': self._make_template_xlsx(),
            'template_filename': 'offline_tool.xlsx',
        })
        action = wizard.action_import()
        template = self.env['rn.gst.excel.template'].browse(action['res_id'])
        self.assertTrue(template.mapping_json)
        self.assertEqual(action['res_model'], 'rn.gst.excel.template')
