# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'rn_gst_tds_tcs')
class TestModuleInstall(TransactionCase):

    def test_module_installed(self):
        module = self.env['ir.module.module'].search([('name', '=', 'rn_gst_tds_tcs')], limit=1)
        self.assertTrue(module, 'Module rn_gst_tds_tcs should be present')
        self.assertEqual(module.state, 'installed')

    def test_security_groups_exist(self):
        # At least one group XML from this module should exist in DB via category link.
        self.assertTrue(
            self.env['ir.model.data'].search([
                ('module', '=', 'rn_gst_tds_tcs'),
                ('model', '=', 'res.groups'),
            ], limit=1),
            'Expected at least one security group XML for rn_gst_tds_tcs',
        )
