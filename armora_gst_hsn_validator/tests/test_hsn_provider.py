# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.armora_gst_hsn_validator.services import hsn_provider


@tagged('post_install', '-at_install', 'armora_gst_hsn')
class TestArmoraGstHsnProviderSkeleton(TransactionCase):

    def test_default_provider_unavailable(self):
        provider = hsn_provider.get_provider(self.env)
        result = provider.verify_code('998314')
        self.assertFalse(result.get('externally_verified'))
        self.assertEqual(result.get('status'), 'unavailable')
        self.assertIn('No authoritative', result.get('message') or '')
