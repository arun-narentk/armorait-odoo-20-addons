# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstBaseGstin(L10nInTestInvoicingCommon):

    def test_valid_gstin(self):
        result = self.env['rn.gst.gstin.validator'].validate('24AAACB6992P1Z3')
        self.assertEqual(result['status'], 'valid')

    def test_invalid_checksum(self):
        result = self.env['rn.gst.gstin.validator'].validate('24AAGCC7144L6ZE')
        self.assertEqual(result['status'], 'invalid')

    def test_normalize(self):
        result = self.env['rn.gst.gstin.validator'].validate('24aaacb6992p1z3')
        self.assertEqual(result['normalized'], '24AAACB6992P1Z3')
