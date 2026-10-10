# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstInvoiceValidator(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref(
            'armora_gst_invoice_validator.group_armora_gst_validator_manager'
        ).id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.default_company.armora_gst_block_post_on_error = True
        cls.default_company.armora_gst_validate_sales = True
        cls.default_company.armora_gst_strict_pos_gstin = True
        cls.partner_a.vat = '24AAPFU0939F1Z1'
        cls.partner_a.l10n_in_gst_treatment = 'regular'
        cls.partner_b.vat = '27AAPFU0939F1ZV'
        cls.partner_b.l10n_in_gst_treatment = 'regular'
        cls.product_a.l10n_in_hsn_code = '998314'

    def _make_draft_invoice(self, partner, taxes, amount=1000.0, invoice_date='2025-04-10'):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=partner,
            amounts=[amount],
            taxes=taxes,
            post=False,
            invoice_date=invoice_date,
        )
        move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product')).write({
            'l10n_in_hsn_code': '998314',
        })
        return move

    def test_ok_intrastate_invoice(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        result = self.env['armora.gst.invoice.validator'].validate_move(move)
        if result['status'] == 'error':
            self.fail('Unexpected errors: %s' % result['issues'])
        move.action_post()
        self.assertEqual(move.state, 'posted')

    def test_pos_gstin_mismatch_blocks_post(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        # Partner GSTIN is Gujarat (24) but force POS to Maharashtra (27)
        move.l10n_in_state_id = self.state_in_mh
        result = self.env['armora.gst.invoice.validator'].validate_move(move)
        self.assertEqual(result['status'], 'error')
        self.assertTrue(any(i['error_type'] == 'pos_gstin_mismatch' for i in result['issues']))
        with self.assertRaises(UserError):
            move.action_post()

    def test_missing_hsn_error(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product')).write({
            'l10n_in_hsn_code': False,
        })
        result = self.env['armora.gst.invoice.validator'].validate_move(move)
        self.assertTrue(any(i['error_type'] == 'missing_hsn' for i in result['issues']))

    def test_score_decreases_with_errors(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        result = self.env['armora.gst.invoice.validator'].validate_move(move)
        self.assertLess(result['score'], 100)
