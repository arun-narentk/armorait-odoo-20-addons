# -*- coding: utf-8 -*-
"""Skeleton tests: format service must not claim government verification."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.armora_gst_hsn_validator.services import hsn_format_validator


@tagged('post_install', '-at_install', 'armora_gst_hsn')
class TestArmoraGstHsnFormatSkeleton(TransactionCase):

    def test_format_stub_does_not_claim_external_verify(self):
        payload = hsn_format_validator.validate_format('998314')
        self.assertIn('format_valid', payload)
        self.assertNotIn('government_verified', payload)
        self.assertNotIn('externally_verified', payload)
