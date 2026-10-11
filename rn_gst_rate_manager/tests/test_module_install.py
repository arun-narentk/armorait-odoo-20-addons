# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'rn_gst_rate')
class TestRnGstRateModuleInstall(TransactionCase):

    def test_models_registered(self):
        for model in (
            'rn.gst.rate',
            'rn.gst.rate.change',
            'rn.gst.rate.history',
            'rn.gst.rate.conflict',
        ):
            self.assertTrue(self.env['ir.model'].search([('model', '=', model)]))

    def test_create_rate_shell(self):
        rate = self.env['rn.gst.rate'].create({
            'name': 'Skeleton GST 18%',
            'code': 'GST_18_SHELL',
            'igst_rate': 18.0,
            'cgst_rate': 9.0,
            'sgst_rate': 9.0,
            'effective_from': '2024-04-01',
        })
        self.assertEqual(rate.company_id, self.env.company)
        self.assertEqual(rate.state, 'draft')
