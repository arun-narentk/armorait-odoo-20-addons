# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'armora_gst_rate')
class TestArmoraGstRateModuleInstall(TransactionCase):

    def test_models_registered(self):
        for model in (
            'armora.gst.rate',
            'armora.gst.rate.change',
            'armora.gst.rate.history',
            'armora.gst.rate.conflict',
        ):
            self.assertTrue(self.env['ir.model'].search([('model', '=', model)]))

    def test_create_rate_shell(self):
        rate = self.env['armora.gst.rate'].create({
            'name': 'Skeleton GST 18%',
            'code': 'GST_18_SHELL',
            'igst_rate': 18.0,
            'cgst_rate': 9.0,
            'sgst_rate': 9.0,
            'effective_from': '2024-04-01',
        })
        self.assertEqual(rate.company_id, self.env.company)
        self.assertEqual(rate.state, 'draft')
