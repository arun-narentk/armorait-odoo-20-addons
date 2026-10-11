# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnEinvoiceMonitor(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_company.l10n_in_edi_feature = True
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False

    def _posted_invoice(self, invoice_date=None):
        move = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], taxes=self.sgst_sale_18,
                                 invoice_date=invoice_date or fields.Date.today())
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _mark_sent(self, move, ack_dt='2025-04-10 10:30:00'):
        attachment = self.env['ir.attachment'].create({
            'name': 'einvoice.json',
            'raw': json.dumps({'Irn': 'a' * 64, 'AckNo': 112510000000001, 'AckDt': ack_dt}).encode(),
            'res_model': 'account.move',
            'res_id': move.id,
            'res_field': 'l10n_in_edi_attachment_file',
            'mimetype': 'application/json',
        })
        move.write({'l10n_in_edi_attachment_id': attachment.id, 'l10n_in_edi_status': 'sent'})

    def test_states(self):
        move = self._posted_invoice()
        self.assertEqual(move.l10n_in_edi_status, 'to_send')
        self.assertEqual(move.rn_einv_state, 'pending')
        move.l10n_in_edi_error = '<p>Invalid GSTIN</p>'
        self.assertEqual(move.rn_einv_state, 'failed')
        move.write({'l10n_in_edi_error': False, 'l10n_in_edi_status': 'cancelled'})
        self.assertEqual(move.rn_einv_state, 'cancelled')

    def test_ack_details_and_cancel_window(self):
        move = self._posted_invoice()
        now_ist = fields.Datetime.now() + timedelta(hours=5, minutes=30)
        self._mark_sent(move, ack_dt=now_ist.strftime('%Y-%m-%d %H:%M:%S'))
        self.env['account.move']._cron_rn_einv_fill_ack()
        self.assertEqual(move.rn_einv_state, 'generated')
        self.assertEqual(move.rn_einv_irn, 'a' * 64)
        self.assertEqual(move.rn_einv_ack_no, '112510000000001')
        self.assertAlmostEqual(move.rn_einv_ack_date, fields.Datetime.now(), delta=timedelta(minutes=2))
        self.assertTrue(move.rn_einv_cancel_open)
        self.assertIn(move, self.env['account.move'].search([('rn_einv_cancel_open', '=', True)]))

        old = self._posted_invoice()
        self._mark_sent(old, ack_dt='2025-04-10 10:30:00')
        old._rn_einv_store_ack()
        self.assertFalse(old.rn_einv_cancel_open)
        self.assertEqual(fields.Datetime.to_string(old.rn_einv_cancel_until), '2025-04-11 05:00:00')

    def test_cancel_needed(self):
        move = self._posted_invoice()
        self._mark_sent(move)
        move.state = 'cancel'
        self.assertEqual(move.rn_einv_state, 'cancel_needed')

    def test_thirty_day_limit(self):
        move = self._posted_invoice(invoice_date=fields.Date.today() - timedelta(days=40))
        self.assertFalse(move.rn_einv_report_by)
        self.assertFalse(move.rn_einv_report_late)
        self.default_company.rn_einv_30_day_rule = True
        self.assertEqual(move.rn_einv_report_by, move.invoice_date + timedelta(days=30))
        self.assertTrue(move.rn_einv_report_late)
        self.assertEqual(move.rn_einv_days_pending, 40)
        self.assertIn(move, self.env['account.move'].search([('rn_einv_report_late', '=', True)]))

    def test_send_again(self):
        ok, bad = self._posted_invoice(), self._posted_invoice()
        bad.l10n_in_edi_error = '<p>Duplicate IRN</p>'

        def fake_send(move):
            if move == bad:
                return {'messages': ['Duplicate IRN']}
            move.l10n_in_edi_status = 'sent'
            return None

        with patch.object(type(self.env['account.move']), '_l10n_in_edi_send_invoice', fake_send):
            result = (ok | bad).action_rn_einv_send_again()
        self.assertIn('1 of 2 sent', result['params']['message'])
        self.assertIn('Duplicate IRN', result['params']['message'])
        self.assertEqual(ok.rn_einv_state, 'generated')
        self.assertEqual(bad.rn_einv_state, 'failed')
