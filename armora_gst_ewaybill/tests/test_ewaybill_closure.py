# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstEwaybillClosure(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('armora_gst_base.group_armora_gst_administrator').id)]
        cls.default_company.armora_gst_enable_ewaybill_closure = True
        cls.default_company.armora_gst_api_environment = 'sandbox'
        cls.default_company.armora_gst_validation_mode = 'blocking'
        # l10n_in demo GSTINs are not checksum-valid; do not block posting for e-waybill tests.
        if 'armora_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.armora_gst_block_post_on_error = False
        cls.move = cls.init_invoice('out_invoice', post=True, products=cls.product_a)
        cls.move.write({
            'armora_ewb_number': '301000000001',
            'armora_ewb_status': 'active',
            'armora_ewb_generation_date': fields.Datetime.to_datetime('2026-08-02 10:00:00'),
            'armora_ewb_validity_date': fields.Datetime.to_datetime('2026-08-10 23:59:59'),
            'armora_ewb_delivery_status': 'delivered',
            'armora_ewb_closure_status': 'open',
        })

    def test_successful_closure(self):
        Service = self.env['armora.gst.ewaybill.close.service']

        def fake_call(self, company, payload):
            return {'success': True, 'data': {'ackNo': 'ACK1'}, 'raw': {'data': {'ackNo': 'ACK1'}}}

        with patch.object(type(Service), '_call_close_api', fake_call):
            result = Service.action_close_ewaybill(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Delivered',
                delivery_date=fields.Date.to_date('2026-08-05'),
            )
        self.assertTrue(result['success'])
        self.assertEqual(self.move.armora_ewb_status, 'closed')
        self.assertEqual(self.move.armora_ewb_closure_status, 'closed')
        audits = self.env['armora.gst.api.audit'].search([
            ('api_type', '=', 'ewaybill_close'),
            ('document_res_id', '=', self.move.id),
        ])
        self.assertTrue(audits)

    def test_invalid_closure_date_before_generation(self):
        Service = self.env['armora.gst.ewaybill.close.service']
        with self.assertRaises(ValidationError):
            Service.validate_closure(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-01'),
                remarks='Too early',
            )

    def test_duplicate_closure_request(self):
        self.move.armora_ewb_closure_requested = True
        self.move.armora_ewb_closure_status = 'requested'
        Service = self.env['armora.gst.ewaybill.close.service']
        with self.assertRaises(UserError):
            Service.validate_closure(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Dup',
            )

    def test_already_closed(self):
        self.move.armora_ewb_status = 'closed'
        self.move.armora_ewb_closure_status = 'closed'
        Service = self.env['armora.gst.ewaybill.close.service']
        with self.assertRaises(UserError):
            Service.validate_closure(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Again',
            )

    def test_cancelled_ewb_closure(self):
        self.move.armora_ewb_status = 'cancelled'
        Service = self.env['armora.gst.ewaybill.close.service']
        with self.assertRaises(UserError):
            Service.validate_closure(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Cancel close',
            )

    def test_api_timeout_retryable(self):
        Service = self.env['armora.gst.ewaybill.close.service']

        def fake_call(self, company, payload):
            return {
                'success': False,
                'error_code': 'timeout',
                'error': 'timeout',
                'retryable': True,
                'raw': {},
            }

        with patch.object(type(Service), '_call_close_api', fake_call):
            result = Service.action_close_ewaybill(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Retry later',
            )
        self.assertFalse(result['success'])
        self.assertTrue(result['retryable'])
        self.assertEqual(self.move.armora_ewb_closure_status, 'failed')

    def test_api_validation_error(self):
        Service = self.env['armora.gst.ewaybill.close.service']

        def fake_call(self, company, payload):
            return {
                'success': False,
                'error_code': 'schema',
                'error': 'bad payload',
                'retryable': True,
                'raw': {'error': [{'code': 'schema', 'message': 'bad payload'}]},
            }

        with patch.object(type(Service), '_call_close_api', fake_call):
            result = Service.action_close_ewaybill(
                self.move,
                ewb_number='301000000001',
                closure_date=fields.Date.to_date('2026-08-05'),
                remarks='Schema',
            )
        self.assertEqual(result['error_code'], 'schema')
