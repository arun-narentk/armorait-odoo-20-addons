# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.rn_gst_debit_note.services import debit_note_detection
from odoo.addons.rn_gst_debit_note.services import debit_note_validation_service


@tagged('post_install', '-at_install', 'rn_gst_debit')
class TestRnGstDebitNoteDetection(TransactionCase):

    def test_refund_is_not_debit_note(self):
        move = self.env['account.move'].new({
            'move_type': 'out_refund',
        })
        self.assertFalse(debit_note_detection.is_debit_note(move))

    def test_validation_stub_is_increase_semantics(self):
        move = self.env['account.move'].new({'move_type': 'out_invoice'})
        result = debit_note_validation_service.validate_debit_note(self.env, move)
        self.assertEqual(result.get('liability_direction'), 'increase')
        self.assertNotEqual(result.get('liability_direction'), 'decrease')
        self.assertNotIn('amount_tax', result)
