# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import ArmoraGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestArmoraGstValidation(ArmoraGstFilingTestCommon):

    def test_validation_detects_missing_hsn(self):
        self.product_a.l10n_in_hsn_code = False
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=False,
            invoice_date='2025-04-10',
        )
        move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product')).write({
            'l10n_in_hsn_code': False,
        })
        move.action_post()
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        filing.action_validate()
        self.assertTrue(
            filing.validation_result_ids.filtered(lambda r: r.error_type == 'missing_hsn')
            or filing.line_ids.filtered(lambda l: l.validation_state == 'error')
        )

    def test_period_filtering(self):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
            taxes=self.sgst_sale_18,
            post=True,
            invoice_date='2025-05-10',
        )
        filing = self._create_gst_filing('04')
        filing.action_load_data()
        self.assertFalse(filing.line_ids.filtered(lambda l: l.move_id == move))
