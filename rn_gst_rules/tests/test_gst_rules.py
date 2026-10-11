# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstRules(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for xmlid in (
            'rn_gst_base.group_rn_gst_user',
            'rn_gst_base.group_rn_gst_manager',
        ):
            group = cls.env.ref(xmlid, raise_if_not_found=False)
            if group:
                cls.env.user.group_ids = [(4, group.id)]

    def test_rule_effective_from_aug_2026(self):
        Rule = self.env['rn.gst.rule']
        self.assertTrue(Rule.rule_applies('EINV_SHIP_TO_GSTIN_REQUIRED', on_date='2026-08-01'))
        self.assertFalse(Rule.rule_applies('EINV_SHIP_TO_GSTIN_REQUIRED', on_date='2026-07-31'))

    def test_ship_to_gstin_required(self):
        Validation = self.env['rn.gst.rule.validation']
        results = Validation.validate_context({
            'ship_details_present': True,
            'ewb_required': True,
            'ship_to_gstin': False,
            'document_date': '2026-08-05',
        })
        codes = [r['code'] for r in results]
        self.assertIn('SHIP_TO_GSTIN_REQUIRED', codes)

    def test_ship_to_not_required_before_effective(self):
        Validation = self.env['rn.gst.rule.validation']
        results = Validation.validate_context({
            'ship_details_present': True,
            'ewb_required': True,
            'ship_to_gstin': False,
            'document_date': '2026-07-01',
        })
        codes = [r['code'] for r in results]
        self.assertNotIn('SHIP_TO_GSTIN_REQUIRED', codes)

    def test_bill_ship_distinct(self):
        Validation = self.env['rn.gst.rule.validation']
        gstin = '24AAACB6992P1Z3'
        results = Validation.validate_bill_to_ship_to_distinct(gstin, gstin, on_date='2026-08-01')
        self.assertTrue(any(r['code'] == 'BILL_SHIP_GSTIN_SAME' for r in results))

    def test_bill_ship_same_allowed_before_effective(self):
        Validation = self.env['rn.gst.rule.validation']
        gstin = '24AAACB6992P1Z3'
        results = Validation.validate_bill_to_ship_to_distinct(gstin, gstin, on_date='2026-07-01')
        self.assertFalse(results)

    def test_invalid_pin(self):
        Validation = self.env['rn.gst.rule.validation']
        results = Validation.validate_pin_code('012345', required=True)
        self.assertTrue(any(r['code'] == 'PIN_CODE_INVALID' for r in results))

    def test_audit_redacts_secrets(self):
        Audit = self.env['rn.gst.api.audit']
        rec = Audit.log_api({
            'company_id': self.default_company.id,
            'api_type': 'ewaybill_close',
            'api_environment': 'sandbox',
            'request_payload': {'ewbNo': '123', 'password': 'secret', 'auth_token': 'tok'},
            'success': False,
        })
        self.assertIn('***REDACTED***', rec.request_payload)
        self.assertNotIn('secret', rec.request_payload)
