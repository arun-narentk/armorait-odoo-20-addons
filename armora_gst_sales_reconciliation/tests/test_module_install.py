# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'armora_gst_sales_reconciliation')
class TestModuleInstall(TransactionCase):

    def test_module_installed(self):
        module = self.env['ir.module.module'].search([('name', '=', 'armora_gst_sales_reconciliation')], limit=1)
        self.assertTrue(module, 'Module armora_gst_sales_reconciliation should be present')
        self.assertEqual(module.state, 'installed')

    def test_security_groups_exist(self):
        # At least one group XML from this module should exist in DB via category link.
        self.assertTrue(
            self.env['ir.model.data'].search([
                ('module', '=', 'armora_gst_sales_reconciliation'),
                ('model', '=', 'res.groups'),
            ], limit=1),
            'Expected at least one security group XML for armora_gst_sales_reconciliation',
        )
