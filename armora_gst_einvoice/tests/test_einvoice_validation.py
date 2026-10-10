# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstEinvoice(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('armora_gst_base.group_armora_gst_administrator').id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.default_company.armora_gst_enable_einvoice = True
        cls.default_company.armora_gst_validation_mode = 'blocking'
        cls.partner_a.vat = '27AAPFU0939F1ZV'
        cls.partner_a.l10n_in_gst_treatment = 'regular'
        cls.ship_partner = cls.partner_a.copy({
            'name': 'Ship To Distinct',
            'vat': '29AAPFU0939F1ZR',
        })
        # Ensure state TIN if available
        mh = cls.env['res.country.state'].search([('l10n_in_tin', '=', '27')], limit=1)
        ka = cls.env['res.country.state'].search([('l10n_in_tin', '=', '29')], limit=1)
        if mh:
            cls.partner_a.state_id = mh
        if ka:
            cls.ship_partner.state_id = ka
            cls.ship_partner.zip = '560001'

    def _make_invoice(self, invoice_date='2026-08-10'):
        move = self.init_invoice('out_invoice', post=False, products=self.product_a, invoice_date=invoice_date)
        move.partner_id = self.partner_a
        move.partner_shipping_id = self.ship_partner
        move.armora_ewb_required = True
        move.armora_ship_to_gstin = self.ship_partner.vat
        move.armora_ship_to_state_code = '29'
        move.armora_ship_to_pin = '560001'
        return move

    def test_valid_b2b_ship_to(self):
        move = self._make_invoice()
        results = move._armora_run_einvoice_validations()
        errors = [r for r in results if r['severity'] == 'error']
        self.assertFalse(errors, results)

    def test_invalid_gstin(self):
        Validation = self.env['armora.gst.validation']
        results = Validation.validate_gstin_value('24AAGCC7144L6ZE')
        self.assertTrue(any(r['code'] == 'GSTIN_INVALID' for r in results))

    def test_bill_ship_same_gstin(self):
        move = self._make_invoice()
        move.armora_ship_to_gstin = move.partner_id.vat
        results = move._armora_run_einvoice_validations()
        self.assertTrue(any(r['code'] == 'BILL_SHIP_GSTIN_SAME' for r in results))

    def test_same_party_shipping_not_blocked(self):
        """Ship-to filled from the buyer itself is not a Bill-to/Ship-to transaction."""
        move = self._make_invoice()
        move.partner_shipping_id = move.partner_id
        move.armora_ship_to_gstin = move.partner_id.vat
        move.armora_ship_to_state_code = '27'
        self.assertFalse(move._armora_ship_details_present())
        results = move._armora_run_einvoice_validations()
        self.assertFalse(any(r['code'] == 'BILL_SHIP_GSTIN_SAME' for r in results), results)
        move._armora_assert_einvoice_validations()

    def test_missing_ship_to_gstin(self):
        move = self._make_invoice()
        move.armora_ship_to_gstin = False
        results = move._armora_run_einvoice_validations()
        self.assertTrue(any(r['code'] == 'SHIP_TO_GSTIN_REQUIRED' for r in results))

    def test_gstin_state_mismatch(self):
        move = self._make_invoice()
        move.armora_ship_to_state_code = '27'
        results = move._armora_run_einvoice_validations()
        self.assertTrue(any(r['code'] == 'GSTIN_STATE_MISMATCH' for r in results))

    def test_invalid_state_code(self):
        results = self.env['armora.gst.validation'].validate_state_code('AB')
        self.assertTrue(any(r['code'] == 'STATE_CODE_INVALID' for r in results))

    def test_invalid_pin(self):
        move = self._make_invoice()
        move.armora_ship_to_pin = '000123'
        results = move._armora_run_einvoice_validations()
        self.assertTrue(any(r['code'] == 'PIN_CODE_INVALID' for r in results))

    def test_valid_pin(self):
        results = self.env['armora.gst.validation'].validate_pin_code('560001', required=True)
        self.assertFalse(results)

    def test_urp_allowed(self):
        move = self._make_invoice()
        move.armora_ship_to_gstin = 'URP'
        move.armora_ship_to_state_code = '29'
        results = move._armora_run_einvoice_validations()
        self.assertFalse(any(r['code'] in ('GSTIN_INVALID', 'SHIP_TO_GSTIN_REQUIRED') for r in results))

    def test_export_expship_gstin(self):
        Validation = self.env['armora.gst.validation']
        results = Validation.validate_export_ship_details(
            {'Gstin': False},
            on_date='2026-08-01',
        )
        self.assertTrue(any(r['code'] == 'EXP_SHIP_GSTIN_REQUIRED' for r in results))

    def test_b2b_ship_lock(self):
        move = self._make_invoice()
        move.l10n_in_gst_treatment = 'regular'
        move.armora_ship_details_locked = True
        with self.assertRaises(UserError):
            move.write({'armora_ship_to_pin': '560002'})

    def test_admin_unlock(self):
        move = self._make_invoice()
        move.armora_ship_details_locked = True
        move.action_armora_unlock_ship_details()
        self.assertFalse(move.armora_ship_details_locked)
