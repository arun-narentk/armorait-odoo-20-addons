# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.rn_gst_hsn_validator.services import hsn_provider


@tagged('post_install', '-at_install', 'rn_gst_hsn')
class TestRnGstHsnProviderSkeleton(TransactionCase):

    def test_default_provider_unavailable(self):
        provider = hsn_provider.get_provider(self.env)
        result = provider.verify_code('998314')
        self.assertFalse(result.get('externally_verified'))
        self.assertEqual(result.get('status'), 'unavailable')
        self.assertIn('No authoritative', result.get('message') or '')
