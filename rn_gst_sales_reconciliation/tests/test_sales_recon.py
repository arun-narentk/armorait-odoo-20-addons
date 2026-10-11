# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

FY = '2025-26'


@tagged('post_install', '-at_install')
class TestRnGstSalesRecon(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_sales_reconciliation.group_rn_gst_sales_recon_user').id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False

    def _invoice(self, amount, date='2025-04-10'):
        move = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[amount], taxes=self.sgst_sale_18,
                                 invoice_date=date)
        move.invoice_line_ids.write({'l10n_in_hsn_code': '998314'})
        move.action_post()
        return move

    def _recon(self):
        recon = self.env['rn.gst.sales.recon'].create({'financial_year': FY, 'return_period': '04'})
        recon.action_run()
        return recon

    def _codes(self, recon):
        return sorted(recon.line_ids.mapped('code'))

    def test_books_and_ledger_totals(self):
        self._invoice(1000.0)
        self._invoice(500.0)
        recon = self._recon()
        self.assertEqual(recon.books_taxable, 1500.0)
        self.assertEqual(recon.books_tax, 270.0)
        self.assertEqual(recon.ledger_tax, 270.0)
        self.assertFalse(recon.line_ids)

    def test_journal_entry_on_output_tax(self):
        self._invoice(1000.0)
        recon = self.env['rn.gst.sales.recon'].create({'financial_year': FY, 'return_period': '04'})
        account = recon._rn_output_tax_accounts()[:1]
        entry = self.env['account.move'].create({
            'move_type': 'entry', 'date': '2025-04-20', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'name': 'Tax on scrap sale', 'account_id': account.id, 'credit': 50.0}),
                Command.create({'name': 'Tax on scrap sale',
                                'account_id': self.company_data['default_account_receivable'].id, 'debit': 50.0}),
            ],
        })
        entry.action_post()
        recon.action_run()
        self.assertEqual(recon.ledger_tax, recon.books_tax + 50.0)
        finding = recon.line_ids.filtered(lambda l: l.code == 'ledger_tax')
        self.assertEqual(finding.move_id, entry)
        self.assertIn('without a sales invoice', finding.message)

    def test_cancelled_invoice(self):
        move = self._invoice(1000.0)
        move.button_draft()
        move.button_cancel()
        recon = self._recon()
        self.assertEqual(self._codes(recon), ['cancelled'])

    def test_against_filed_gstr1(self):
        if 'rn.gst.filing' not in self.env:
            self.skipTest('Armora GST Filing is not installed.')
        filed_same = self._invoice(1000.0)
        filed_changed = self._invoice(500.0)
        added = self._invoice(300.0)
        dropped = self._invoice(200.0)
        filing = self.env['rn.gst.filing'].sudo().create({
            'company_id': self.default_company.id, 'gstin': self.default_company.vat,
            'financial_year': FY, 'return_period': '04', 'filing_type': 'gstr1', 'filing_frequency': 'monthly',
        })
        lines = [(filed_same, 1000.0, 90.0), (filed_changed, 400.0, 36.0), (dropped, 200.0, 18.0)]
        self.env['rn.gst.filing.line'].sudo().create([{
            'filing_id': filing.id, 'move_id': move.id, 'invoice_number': move.name, 'taxable_value': taxable,
            'cgst_amount': half, 'sgst_amount': half,
        } for move, taxable, half in lines])
        filing.sudo().write({'state': 'filed'})
        dropped.button_draft()
        dropped.button_cancel()

        recon = self._recon()
        self.assertTrue(recon.filing_ref)
        by_code = {l.code: l for l in recon.line_ids}
        self.assertEqual(by_code['added_after_filing'].move_id, added)
        self.assertEqual(by_code['changed_after_filing'].move_id, filed_changed)
        self.assertEqual(by_code['removed_after_filing'].move_id, dropped)
        self.assertEqual(by_code['changed_after_filing'].difference, 100.0)
        self.assertEqual(recon.error_count, 3)

    def test_review_kept_on_rerun(self):
        move = self._invoice(1000.0)
        move.button_draft()
        move.button_cancel()
        recon = self._recon()
        recon.line_ids.note = 'Wrong customer, re-issued'
        recon.line_ids.action_ignore()
        recon.action_run()
        self.assertEqual(recon.line_ids.state, 'ignored')
        self.assertEqual(recon.open_count, 0)
