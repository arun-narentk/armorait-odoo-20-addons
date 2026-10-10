# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import tagged
from .common import ArmoraGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestArmoraGstFilingSecurity(ArmoraGstFilingTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filing_user = cls.env['res.users'].create({
            'name': 'GST Filing User Test',
            'login': 'gst_filing_user_test',
            'group_ids': [(6, 0, [
                cls.env.ref('armora_gst_filing.group_armora_gst_filing_user').id,
                cls.env.ref('base.group_user').id,
                cls.env.ref('account.group_account_invoice').id,
            ])],
            'company_id': cls.default_company.id,
            'company_ids': [(6, 0, [cls.default_company.id])],
        })
        cls.filing_manager = cls.env['res.users'].create({
            'name': 'GST Filing Manager Test',
            'login': 'gst_filing_manager_test',
            'group_ids': [(6, 0, [
                cls.env.ref('armora_gst_filing.group_armora_gst_filing_manager').id,
                cls.env.ref('base.group_user').id,
                cls.env.ref('account.group_account_invoice').id,
            ])],
            'company_id': cls.default_company.id,
            'company_ids': [(6, 0, [cls.default_company.id])],
        })

    def test_user_cannot_delete_filing(self):
        filing = self._create_gst_filing('04')
        with self.assertRaises(AccessError):
            filing.with_user(self.filing_user).unlink()

    def test_user_cannot_import_template(self):
        with self.assertRaises(AccessError):
            self.env['armora.gst.excel.template.import.wizard'].with_user(
                self.filing_user
            ).create({
                'name': 'Blocked',
                'template_file': b'dummy',
            })

    def test_manager_can_delete_draft_filing(self):
        filing = self._create_gst_filing('05')
        filing.with_user(self.filing_manager).unlink()
        self.assertFalse(filing.exists())

    def test_multi_company_record_rule(self):
        other_company = self.env['res.company'].create({
            'name': 'Other GST Co',
            'vat': self.valid_company_gstin,
        })
        filing_a = self._create_gst_filing('04')
        filing_b = self.env['armora.gst.filing'].with_company(other_company).create({
            'company_id': other_company.id,
            'gstin': other_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'filing_type': 'gstr1',
            'filing_frequency': 'monthly',
            'period_start': filing_a.period_start,
            'period_end': filing_a.period_end,
        })
        user_b = self.env['res.users'].create({
            'name': 'Other Co User',
            'login': 'gst_other_co_user',
            'group_ids': [(6, 0, [
                self.env.ref('armora_gst_filing.group_armora_gst_filing_user').id,
                self.env.ref('base.group_user').id,
                self.env.ref('account.group_account_invoice').id,
            ])],
            'company_id': other_company.id,
            'company_ids': [(6, 0, [other_company.id])],
        })
        visible = self.env['armora.gst.filing'].with_user(user_b).search([
            ('id', 'in', [filing_a.id, filing_b.id]),
        ])
        self.assertEqual(visible, filing_b)
