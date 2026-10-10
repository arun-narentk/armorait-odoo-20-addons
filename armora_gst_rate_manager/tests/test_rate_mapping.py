# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.armora_gst_rate_manager.services import rate_mapping_service


@tagged('post_install', '-at_install', 'armora_gst_rate')
class TestArmoraGstRateMappingSkeleton(TransactionCase):

    def test_mapping_stub_is_read_oriented(self):
        result = rate_mapping_service.validate_tax_mapping(self.env)
        self.assertEqual(result.get('status'), 'pending')
        mapping = rate_mapping_service.get_odoo_tax_mapping(self.env)
        self.assertIn('igst_tax', mapping)
        self.assertIn('group_tax', mapping)
