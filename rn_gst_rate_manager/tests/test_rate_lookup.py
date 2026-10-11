# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.rn_gst_rate_manager.services import rate_lookup_service


@tagged('post_install', '-at_install', 'rn_gst_rate')
class TestRnGstRateLookupSkeleton(TransactionCase):

    def test_lookup_stub_does_not_return_invoice_amounts(self):
        result = rate_lookup_service.get_rate(self.env, {'hsn_sac': '998314'})
        self.assertIn('status', result)
        self.assertNotIn('amount_tax', result)
        self.assertNotIn('invoice_total', result)
