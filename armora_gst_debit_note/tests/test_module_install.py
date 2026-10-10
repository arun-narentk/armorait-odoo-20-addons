# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'armora_gst_debit')
class TestArmoraGstDebitNoteModuleInstall(TransactionCase):

    def test_models_registered(self):
        self.assertTrue(self.env['ir.model'].search([
            ('model', '=', 'armora.gst.debit.note.reason'),
        ]))
        self.assertTrue(self.env['ir.model'].search([
            ('model', '=', 'armora.gst.debit.note.validation'),
        ]))

    def test_create_reason_shell(self):
        reason = self.env['armora.gst.debit.note.reason'].create({
            'name': 'Additional taxable value',
            'code': 'ADDITIONAL_VALUE',
        })
        self.assertTrue(reason.require_original_invoice)
        self.assertTrue(reason.gst_applicable)
