# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstCreditNote(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.reason_return = cls.env.ref('rn_gst_credit_note.reason_sales_return')
        cls.reason_financial = cls.env.ref('rn_gst_credit_note.reason_financial')
        cls.invoice = cls._post_invoice([1000.0], cls.sgst_sale_18, '2025-04-10')

    @classmethod
    def _post_invoice(cls, amounts, taxes, invoice_date, partner=None):
        move = cls.init_invoice('out_invoice', partner=partner or cls.partner_a, amounts=amounts, taxes=taxes,
                                invoice_date=invoice_date)
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _credit_note(self, invoice, note_date='2025-05-01', amount=None, reason=None):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({
            'date': note_date,
            'journal_id': invoice.journal_id.id,
            'rn_cn_reason_id': (reason or self.reason_return).id,
        })
        note = self.env['account.move'].browse(wizard.reverse_moves()['res_id'])
        if amount is not None:
            note.invoice_line_ids.price_unit = amount
        return note

    def test_partial_credit_note_ok(self):
        note = self._credit_note(self.invoice, amount=400.0)
        self.assertEqual(note.rn_cn_reason_id, self.reason_return)
        self.assertEqual(note.rn_cn_check_state, 'ok')
        self.assertEqual(note.rn_cn_deadline, date(2026, 11, 30))
        note.action_post()
        self.assertEqual(self.invoice.rn_cn_credited_amount, 400.0)
        self.assertEqual(self.invoice.rn_cn_remaining_amount, 600.0)

    def test_more_than_invoice(self):
        self._credit_note(self.invoice, amount=400.0).action_post()
        second = self._credit_note(self.invoice, amount=700.0)
        self.assertEqual(second.rn_cn_check_state, 'error')
        self.assertIn('more than its taxable value', second.rn_cn_check_messages)
        second.invoice_line_ids.price_unit = 600.0
        self.assertEqual(second.rn_cn_check_state, 'ok')

    def test_section34_time_limit(self):
        on_time = self._credit_note(self.invoice, note_date='2026-11-30', amount=100.0)
        self.assertEqual(on_time.rn_cn_check_state, 'ok')
        late = self._credit_note(self.invoice, note_date='2026-12-01', amount=100.0)
        self.assertEqual(late.rn_cn_check_state, 'error')
        self.assertIn('section 34', late.rn_cn_check_messages)

    def test_rates_and_tax_type(self):
        note = self._credit_note(self.invoice, amount=100.0)
        note.invoice_line_ids.tax_ids = self.sgst_sale_5
        self.assertEqual(note.rn_cn_check_state, 'error')
        self.assertIn('not on the original invoice', note.rn_cn_check_messages)
        note.invoice_line_ids.tax_ids = self.igst_sale_18
        self.assertIn('IGST against CGST/SGST', note.rn_cn_check_messages)

    def test_financial_credit_note(self):
        note = self.init_invoice('out_refund', partner=self.partner_a, amounts=[100.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-06-01')
        note.rn_cn_reason_id = self.reason_financial
        self.assertEqual(note.rn_cn_check_state, 'error')
        self.assertIn('must not carry GST', note.rn_cn_check_messages)
        note.invoice_line_ids.tax_ids = False
        self.assertEqual(note.rn_cn_check_state, 'ok')

    def test_missing_original_and_reason(self):
        note = self.init_invoice('out_refund', partner=self.partner_a, amounts=[100.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-06-01')
        self.assertEqual(note.rn_cn_check_state, 'warning')
        self.assertIn('No credit note reason', note.rn_cn_check_messages)
        note.rn_cn_reason_id = self.reason_return
        self.assertEqual(note.rn_cn_check_state, 'error')
        self.assertIn('Link the original invoice', note.rn_cn_check_messages)

    def test_other_partner(self):
        note = self._credit_note(self.invoice, amount=100.0)
        note.partner_id = self.partner_b
        self.assertEqual(note.rn_cn_check_state, 'error')

    def test_block_posting_setting(self):
        # Invoice of FY 2024-25: the GST time limit was 30 November 2025.
        old_invoice = self._post_invoice([1000.0], self.sgst_sale_18, '2024-05-10')
        late = self._credit_note(old_invoice, note_date='2026-01-15', amount=100.0)
        self.assertEqual(late.rn_cn_check_state, 'error')
        self.default_company.rn_gst_cn_block_on_error = True
        with self.assertRaises(UserError):
            late.action_post()
        self.default_company.rn_gst_cn_block_on_error = False
        late.action_post()
        self.assertEqual(late.state, 'posted')

    def test_vendor_credit_note(self):
        bill = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[500.0], taxes=self.sgst_purchase_5,
                                 invoice_date='2025-04-10')
        bill.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        bill.action_post()
        note = self._credit_note(bill, amount=600.0)
        self.assertEqual(note.move_type, 'in_refund')
        self.assertEqual(note.rn_cn_check_state, 'error')
