# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstInvoiceCompliance(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_invoice_compliance.group_rn_gst_compliance_manager').id)]
        # Checksum-valid GSTINs, so that the validator only reports what each test sets up.
        cls.default_company.vat = '24AAGCC7144L6ZD'
        cls.partner_a.vat = '24ABCPM8965E1ZJ'
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.reviewer = cls.env['res.users'].create({
            'name': 'GST Reviewer', 'login': 'gst_reviewer_test',
            'group_ids': [(6, 0, [
                cls.env.ref('account.group_account_invoice').id,
                cls.env.ref('rn_gst_invoice_compliance.group_rn_gst_compliance_reviewer').id,
            ])],
            'company_id': cls.default_company.id, 'company_ids': [(6, 0, cls.default_company.ids)],
        })

    def _invoice(self, hsn='998314'):
        move = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-04-10')
        move.invoice_line_ids.write({'l10n_in_hsn_code': hsn})
        return move

    def test_readiness_follows_validator(self):
        move = self._invoice(hsn=False)
        self.assertEqual(move.rn_gst_readiness, 'not_checked')
        move.action_rn_gst_validate()
        self.assertEqual(move.rn_gst_validation_status, 'error')
        self.assertEqual(move.rn_gst_readiness, 'blocked')
        self.assertIn('GST validation error', move.rn_gst_readiness_reasons)

        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_rn_gst_validate()
        self.assertIn(move.rn_gst_validation_status, ('ok', 'warning'))
        self.assertIn(move.rn_gst_readiness, ('ready', 'review'))

    def test_review_and_approval(self):
        move = self._invoice()
        move.write({'rn_gst_validation_status': 'warning', 'rn_gst_validation_score': 95})
        self.assertEqual(move.rn_gst_readiness, 'review')

        move.with_user(self.reviewer)._rn_gst_approve('Checked with the customer')
        self.assertEqual(move.rn_gst_readiness, 'approved')
        self.assertEqual(move.rn_gst_reviewer_id, self.reviewer)

        # A new problem after approval sends it back.
        move.rn_gst_validation_status = 'error'
        self.assertEqual(move.rn_gst_readiness, 'blocked')

        # Only a manager approves a blocked invoice, and only with a note.
        with self.assertRaises(AccessError):
            move.with_user(self.reviewer)._rn_gst_approve('ok')
        with self.assertRaises(UserError):
            move._rn_gst_approve(False)
        move._rn_gst_approve('Validator rule does not apply to this customer')
        self.assertEqual(move.rn_gst_readiness, 'approved')
        move.action_rn_gst_reset_review()
        self.assertEqual(move.rn_gst_readiness, 'blocked')

    def test_einvoice_irn_missing_blocks(self):
        if 'l10n_in_edi_status' not in self.env['account.move']._fields:
            self.skipTest('Indian e-invoicing is not installed.')
        move = self._invoice()
        move.action_post()
        move.write({'rn_gst_validation_status': 'ok', 'l10n_in_edi_status': 'to_send'})
        self.assertEqual(move.rn_gst_readiness, 'blocked')
        self.assertIn('IRN not generated', move.rn_gst_readiness_reasons)
        move.l10n_in_edi_status = 'sent'
        self.assertEqual(move.rn_gst_readiness, 'ready')

    def test_tax_type_mismatch_blocks(self):
        if 'rn_gst_tax_mismatch' not in self.env['account.move']._fields:
            self.skipTest('Armora GST Multi-GSTIN is not installed.')
        move = self.init_invoice('out_invoice', partner=self.partner_b, amounts=[1000.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-04-10')
        move.rn_gst_validation_status = 'ok'
        self.assertTrue(move.rn_gst_tax_mismatch)
        self.assertEqual(move.rn_gst_readiness, 'blocked')

    def test_wizard_and_list_buttons(self):
        moves = self._invoice() | self._invoice(hsn=False)
        result = moves.action_rn_gst_validate_selected()
        self.assertEqual(result['params']['message'], '2 invoice(s) checked.')
        action = moves.action_rn_gst_approve()
        wizard = self.env[action['res_model']].with_context(action['context']).create({'note': 'Year-end review'})
        self.assertEqual(wizard.blocked_count, 1)
        wizard.action_approve()
        self.assertTrue(all(m.rn_gst_readiness in ('approved', 'ready') for m in moves))
