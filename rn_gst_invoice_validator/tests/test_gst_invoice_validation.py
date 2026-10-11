# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstInvoiceValidationRun(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref(
            'rn_gst_invoice_validator.group_rn_gst_validator_manager'
        ).id)]
        cls.default_company.vat = '24AAACB6992P1Z3'
        cls.default_company.rn_gst_block_post_on_error = True
        cls.default_company.rn_gst_validate_sales = True
        cls.default_company.rn_gst_strict_pos_gstin = True
        cls.partner_a.vat = '24AAPFU0939F1Z1'
        cls.partner_a.l10n_in_gst_treatment = 'regular'
        cls.partner_b.vat = '27AAPFU0939F1ZV'
        cls.partner_b.l10n_in_gst_treatment = 'regular'
        cls.product_a.l10n_in_hsn_code = '998314'
        cls.Validation = cls.env['rn.gst.invoice.validation']

    def _make_draft_invoice(self, partner, taxes, amount=1000.0, invoice_date='2025-04-10'):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=partner,
            amounts=[amount],
            taxes=taxes,
            post=False,
            invoice_date=invoice_date,
        )
        move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product')).write({
            'l10n_in_hsn_code': '998314',
        })
        return move

    def test_single_invoice_run_completed(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        run = self.Validation.create_for_invoices(move)
        self.assertEqual(run.state, 'completed')
        self.assertEqual(run.total_invoices, 1)
        self.assertGreaterEqual(run.duration, 0.0)
        self.assertTrue(run.name)
        self.assertNotEqual(run.name, 'New')

    def test_run_creates_results_for_errors(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        run = self.Validation.create_for_invoices(move)
        self.assertEqual(run.state, 'completed')
        self.assertGreater(run.error_count, 0)
        self.assertTrue(any(r.rule_code == 'POS_GSTIN_MISMATCH' for r in run.result_ids))
        self.assertTrue(all(r.blocking for r in run.result_ids.filtered(lambda r: r.severity == 'error')))

    def test_rerun_clears_duplicates_on_same_run(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        run = self.Validation.create_for_invoices(move)
        first_count = len(run.result_ids)
        self.assertGreater(first_count, 0)
        run.action_rerun_validation()
        self.assertEqual(run.state, 'completed')
        self.assertEqual(len(run.result_ids), first_count)
        keys = run.result_ids.mapped('dedupe_key')
        self.assertEqual(len(keys), len(set(keys)))

    def test_history_preserved_across_runs(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        run1 = self.Validation.create_for_invoices(move)
        run2 = self.Validation.create_for_invoices(move)
        self.assertNotEqual(run1.id, run2.id)
        self.assertTrue(run1.result_ids)
        self.assertTrue(run2.result_ids)
        self.assertEqual(run1.state, 'completed')
        self.assertEqual(run2.state, 'completed')

    def test_batch_validation(self):
        move_ok = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move_bad = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move_bad.l10n_in_state_id = self.state_in_mh
        run = self.Validation.create_for_invoices(move_ok | move_bad)
        self.assertEqual(run.total_invoices, 2)
        self.assertEqual(run.valid_invoices, 1)
        self.assertGreater(run.error_count, 0)

    def test_does_not_alter_accounting_amounts(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        amount_untaxed = move.amount_untaxed
        amount_tax = move.amount_tax
        partner_vat = move.partner_id.vat
        run = self.Validation.create_for_invoices(move)
        self.assertEqual(run.state, 'completed')
        self.assertEqual(move.amount_untaxed, amount_untaxed)
        self.assertEqual(move.amount_tax, amount_tax)
        self.assertEqual(move.partner_id.vat, partner_vat)

    def test_company_mismatch_rejected(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        other = self._create_company(
            name='Other IN Co',
            country_id=self.country_in.id,
            state_id=self.state_in_gj.id,
        )
        with self.assertRaises(ValidationError):
            self.Validation.create({
                'company_id': other.id,
                'invoice_ids': [(6, 0, move.ids)],
            })

    def test_mark_reviewed(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        run = self.Validation.create_for_invoices(move)
        self.assertTrue(run.result_ids.filtered(lambda r: r.status == 'open'))
        run.action_mark_reviewed()
        self.assertTrue(all(r.status == 'resolved' for r in run.result_ids))

    def test_empty_run_raises(self):
        run = self.Validation.create({'company_id': self.default_company.id})
        with self.assertRaises(UserError):
            run.action_run_validation()

    def test_sync_move_issues_optional(self):
        move = self._make_draft_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = self.state_in_mh
        run = self.Validation.create({
            'company_id': self.default_company.id,
            'invoice_ids': [(6, 0, move.ids)],
            'sync_move_issues': False,
        })
        run.action_run_validation()
        self.assertTrue(run.result_ids)
        self.assertFalse(move.rn_gst_issue_ids)
