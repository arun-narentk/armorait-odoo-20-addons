# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGstGstin(RnGstFilingTestCommon):

    def test_gstin_valid_structure(self):
        Validator = self.env['rn.gst.gstin.validator']
        result = Validator.validate(self.valid_company_gstin)
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(result['normalized'], self.valid_company_gstin)

    def test_gstin_normalize_lowercase(self):
        Validator = self.env['rn.gst.gstin.validator']
        result = Validator.validate(self.valid_company_gstin.lower())
        self.assertEqual(result['normalized'], self.valid_company_gstin)

    def test_gstin_missing(self):
        result = self.env['rn.gst.gstin.validator'].validate('')
        self.assertEqual(result['status'], 'invalid')

    def test_gstin_bad_length(self):
        result = self.env['rn.gst.gstin.validator'].validate('24AAGCC7144L6')
        self.assertEqual(result['status'], 'invalid')

    def test_gstin_bad_checksum(self):
        result = self.env['rn.gst.gstin.validator'].validate('24AAGCC7144L6ZE')
        self.assertEqual(result['status'], 'invalid')
