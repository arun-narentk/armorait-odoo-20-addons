# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstEwaybillEdiSync(L10nInTestInvoicingCommon):
    """Regression: EWBs generated on l10n.in.ewaybill must sync Armora fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('armora_gst_base.group_armora_gst_administrator').id)]
        cls.default_company.armora_gst_api_environment = 'sandbox'
        cls.default_company.armora_gst_post_closure_actions_allowed = False
        if 'armora_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.armora_gst_block_post_on_error = False
        cls.move = cls.init_invoice('out_invoice', post=True, products=cls.product_a)
        cls.ewaybill = cls.env['l10n.in.ewaybill'].create({
            'type_id': cls.env.ref('l10n_in_ewaybill.type_tax_invoice_sub_type_supply').id,
            'account_move_id': cls.move.id,
            'transporter_id': cls.partner_a.id,
            'mode': '1',
            'vehicle_no': 'GJ11AA1234',
            'vehicle_type': 'R',
            'distance': 20,
        })

    def test_sync_from_irn_response_payload(self):
        self.move._armora_sync_ewb_from_response({
            'EwbNo': '301000000099',
            'EwbDt': '05/08/2026 10:00:00',
            'EwbValidTill': '10/08/2026 23:59:00',
            'Irn': 'IRN-TEST-001',
        })
        self.assertEqual(self.move.armora_ewb_number, '301000000099')
        self.assertEqual(self.move.armora_ewb_status, 'active')
        self.assertEqual(self.move.armora_ewb_irn, 'IRN-TEST-001')
        self.assertEqual(self.move.armora_ewb_closure_status, 'open')

    def test_generated_ewaybill_syncs_invoice_and_audits(self):
        self.ewaybill._write_successfully_response({
            'name': '301000000123',
            'state': 'generated',
            'ewaybill_date': '2026-08-05',
            'ewaybill_expiry_date': '2026-08-10',
        })
        for record in (self.ewaybill, self.move):
            self.assertEqual(record.armora_ewb_number, '301000000123')
            self.assertEqual(record.armora_ewb_status, 'active')
            self.assertEqual(record.armora_ewb_vehicle_no, 'GJ11AA1234')
            self.assertEqual(record.armora_ewb_transporter_id, self.partner_a)
        audits = self.env['armora.gst.api.audit'].search([
            ('api_type', '=', 'ewaybill_generate'),
            ('document_res_id', '=', self.move.id),
            ('success', '=', True),
        ])
        self.assertTrue(audits)

    def test_cancelled_ewaybill_syncs_cancel_status(self):
        self.ewaybill._write_successfully_response({
            'name': '301000000124',
            'state': 'generated',
            'ewaybill_date': '2026-08-05',
        })
        self.ewaybill._write_successfully_response({'state': 'cancel'})
        self.assertEqual(self.ewaybill.armora_ewb_status, 'cancelled')
        self.assertEqual(self.move.armora_ewb_status, 'cancelled')
        self.assertEqual(self.move.armora_ewb_number, '301000000124')

    def test_post_closure_blocks_vehicle_edit_on_move(self):
        self.move.write({
            'armora_ewb_status': 'closed',
            'armora_ewb_closure_status': 'closed',
            'armora_ewb_number': '301000000001',
        })
        with self.assertRaises(UserError):
            self.move.write({'armora_ewb_vehicle_no': 'KA01AB1234'})

    def test_failed_armora_sync_keeps_generated_ewaybill(self):
        """A blocked invoice-side sync must not undo the portal response."""
        self.move.write({'armora_ewb_status': 'closed', 'armora_ewb_number': '301000000002'})
        self.ewaybill._write_successfully_response({
            'name': '301000000200',
            'state': 'generated',
            'ewaybill_date': '2026-08-05',
        })
        self.assertEqual(self.ewaybill.state, 'generated')
        self.assertEqual(self.ewaybill.name, '301000000200')
