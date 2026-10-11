# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstEinvoiceEdiHooks(L10nInTestInvoicingCommon):
    """Regression for the Odoo 20 e-invoice hooks on account.move."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_base.group_rn_gst_administrator').id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.default_company.l10n_in_edi_feature = True
        cls.default_company.rn_gst_enable_einvoice = True
        cls.default_company.rn_gst_validation_mode = 'blocking'
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            # Invoice Validator (when installed) checks POS vs GSTIN state, not under test here.
            cls.default_company.rn_gst_block_post_on_error = False
        cls.partner_a.vat = '27AAPFU0939F1ZV'
        cls.partner_a.l10n_in_gst_treatment = 'regular'
        cls.ship_partner = cls.partner_a.copy({
            'name': 'Ship To Distinct',
            'vat': '29AAPFU0939F1ZR',
        })
        ka = cls.env['res.country.state'].search([('l10n_in_tin', '=', '29')], limit=1)
        if ka:
            cls.ship_partner.state_id = ka
            cls.ship_partner.zip = '560001'

    def _make_invoice(self, invoice_date='2026-08-10'):
        move = self.init_invoice(
            'out_invoice', post=False, products=self.product_a, invoice_date=invoice_date
        )
        move.partner_id = self.partner_a
        move.partner_shipping_id = self.ship_partner
        move.l10n_in_gst_treatment = 'regular'
        move.rn_ewb_required = True
        move.rn_ship_to_gstin = self.ship_partner.vat
        move.rn_ship_to_state_code = '29'
        move.rn_ship_to_pin = '560001'
        return move

    def test_after_einvoice_success_locks_and_audits(self):
        move = self._make_invoice()
        self.assertFalse(move.rn_ship_details_locked)
        move._rn_after_einvoice_success()
        self.assertTrue(move.rn_ship_details_locked)
        audits = self.env['rn.gst.api.audit'].search([
            ('api_type', '=', 'einvoice_generate'),
            ('document_res_id', '=', move.id),
            ('success', '=', True),
        ])
        self.assertTrue(audits)

    def test_send_blocked_by_rn_validation(self):
        """A blocking Armora error must stop the send before the portal is called."""
        move = self._make_invoice()
        move.rn_ship_to_gstin = 'NOT-A-GSTIN'
        with patch.object(type(move), '_l10n_in_edi_connect_to_server') as connect:
            result = move._l10n_in_edi_send_invoice()
        connect.assert_not_called()
        self.assertTrue(result and result.get('messages'))
        self.assertTrue(move.l10n_in_edi_error)
        self.assertNotEqual(move.l10n_in_edi_status, 'sent')

    def test_send_success_locks_ship_details(self):
        move = self._make_invoice()
        move.action_post()
        response = {'data': {'Irn': 'IRN-ARMORA-001', 'AckNo': 1, 'AckDt': '2026-08-10 10:00:00'}}
        with patch.object(type(move), '_l10n_in_edi_connect_to_server', return_value=response):
            result = move._l10n_in_edi_send_invoice()
        self.assertFalse(result)
        self.assertEqual(move.l10n_in_edi_status, 'sent')
        self.assertEqual(move.rn_irn, 'IRN-ARMORA-001')
        self.assertEqual(move.rn_einvoice_status, 'sent')
        self.assertTrue(move.rn_ship_details_locked)

    def test_generate_json_uses_rn_ship_details(self):
        move = self._make_invoice()
        move.rn_ship_to_trade_name = 'Ship Trade Name'
        move.action_post()
        payload = move._l10n_in_edi_generate_invoice_json()
        self.assertEqual(payload['ShipDtls']['GSTIN'], '29AAPFU0939F1ZR')
        self.assertEqual(payload['ShipDtls']['TrdNm'], 'Ship Trade Name')
        self.assertEqual(payload['ShipDtls']['Pin'], 560001)

    def test_manual_ship_details_without_distinct_partner(self):
        move = self._make_invoice()
        move.partner_shipping_id = move.partner_id
        move.rn_ship_to_gstin = '29AAPFU0939F1ZR'
        move.rn_ship_to_state_code = '29'
        move.rn_ship_to_pin = '560001'
        self.assertTrue(move._rn_ship_details_present())

    def _make_sent_invoice_with_ewaybill(self):
        move = self._make_invoice()
        move.action_post()
        attachment = self.env['ir.attachment'].create({
            'name': 'einvoice_rn.json',
            'res_model': 'account.move',
            'res_id': move.id,
            'raw': b'{"Irn": "IRN-ARMORA-EWB"}',
        })
        move.write({'l10n_in_edi_status': 'sent', 'l10n_in_edi_attachment_id': attachment.id})
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'account_move_id': move.id,
            'distance': 20,
            'mode': '1',
            'vehicle_no': 'GJ11AA1234',
            'vehicle_type': 'R',
        })
        return move, ewaybill

    def test_ewaybill_by_irn_blocked_by_rn_validation(self):
        move, ewaybill = self._make_sent_invoice_with_ewaybill()
        self.assertTrue(ewaybill.is_process_through_irn)
        move.rn_ship_to_gstin = 'NOT-A-GSTIN'
        with patch.object(type(move), '_l10n_in_edi_connect_to_server') as connect:
            self.assertFalse(ewaybill._generate_ewaybill_by_irn())
        connect.assert_not_called()
        self.assertTrue(ewaybill.error_message)
        self.assertEqual(ewaybill.state, 'pending')

    def test_ewaybill_by_irn_payload_uses_rn_ship_details(self):
        move, ewaybill = self._make_sent_invoice_with_ewaybill()
        move.rn_exp_ship_gstin = '29AAPFU0939F1ZR'
        move.rn_exp_ship_trade_name = 'Consignee Trade'
        payload = ewaybill._ewaybill_generate_irn_json()
        self.assertEqual(payload['ExpShipDtls']['Gstin'], '29AAPFU0939F1ZR')
        self.assertEqual(payload['ExpShipDtls']['TrdNm'], 'Consignee Trade')
