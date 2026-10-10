# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'armora_gst_hsn')
class TestArmoraGstHsnModuleInstall(TransactionCase):

    def test_models_registered(self):
        self.assertTrue(self.env['ir.model'].search([
            ('model', '=', 'armora.gst.hsn.validation.result'),
        ]))
        self.assertTrue(self.env['ir.model'].search([
            ('model', '=', 'armora.gst.hsn.validation.run'),
        ]))
        self.assertTrue(self.env['ir.model'].search([
            ('model', '=', 'armora.gst.hsn.validation.rule'),
        ]))

    def test_create_result_shell(self):
        result = self.env['armora.gst.hsn.validation.result'].create({
            'name': 'Skeleton result',
        })
        self.assertEqual(result.company_id, self.env.company)
