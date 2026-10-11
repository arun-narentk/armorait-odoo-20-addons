# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import BinaryBytes
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'rn_gst_tds_tcs')
class TestRnGstTdsTcs(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_tds_tcs.group_rn_gst_tds_tcs_manager').id)]
        company = cls.default_company
        if 'rn_gst_block_post_on_error' in company._fields:
            company.rn_gst_block_post_on_error = False
        # partner_a is in the company's state, partner_b in another state.
        cls.partner_a.rn_gst_tds_deductor = True
        cls.partner_b.rn_gst_tcs_operator = True
        cls._invoice(cls.partner_a, 300000.0)
        cls._invoice(cls.partner_a, 200000.0)  # below the 2.5 lakh threshold
        cls._invoice(cls.partner_b, 100000.0)
        cls._invoice(cls.partner_b, 20000.0, move_type='out_refund')
        cls.period = cls.env['rn.gst.tds.tcs.period'].create({
            'company_id': company.id,
            'financial_year': '2025-26',
            'return_period': '04',
        })

    @classmethod
    def _invoice(cls, partner, amount, move_type='out_invoice'):
        move = cls.init_invoice(move_type, partner=partner, invoice_date='2025-04-15', amounts=[amount])
        move.invoice_line_ids.l10n_in_hsn_code = '998314'
        move.action_post()
        return move

    def _credit(self, credit_type):
        return self.period.credit_ids.filtered(lambda c: c.credit_type == credit_type)

    def _import(self, credit_type, csv_text):
        wizard = self.env['rn.gst.tds.tcs.import.wizard'].create({
            'period_id': self.period.id,
            'credit_type': credit_type,
            'data_file': BinaryBytes(csv_text.encode()),
            'filename': 'gstr2x.csv',
        })
        wizard.action_import()

    def test_expected_credits(self):
        self.assertTrue(self.period.name.startswith('TDSTCS/'))
        self.assertEqual(self.period.gstin, self.default_company.vat)
        self.period.action_compute_expected()
        self.assertEqual(self.period.state, 'computed')
        tds = self._credit('tds')
        self.assertEqual(tds.partner_id, self.partner_a)
        self.assertEqual(tds.deductor_gstin, self.partner_a.vat)
        self.assertEqual(len(tds.invoice_ids), 1, 'Only the invoice above the threshold counts.')
        self.assertAlmostEqual(tds.expected_taxable, 300000.0)
        self.assertAlmostEqual(tds.expected_cgst, 3000.0)
        self.assertAlmostEqual(tds.expected_sgst, 3000.0)
        self.assertAlmostEqual(tds.expected_igst, 0.0)
        tcs = self._credit('tcs')
        self.assertEqual(tcs.partner_id, self.partner_b)
        self.assertAlmostEqual(tcs.expected_taxable, 80000.0, msg='Credit notes reduce the TCS value.')
        self.assertAlmostEqual(tcs.expected_igst, 400.0)
        self.assertEqual(tcs.match_state, 'expected_only')
        self.assertAlmostEqual(self.period.expected_total, 6400.0)

    def test_import_match_accept(self):
        account = self.env['account.account'].create({
            'name': 'GST TDS/TCS Receivable', 'code': 'TDSREC', 'account_type': 'asset_current',
        })
        self.default_company.write({
            'rn_gst_tds_tcs_account_id': account.id,
            'rn_gst_tds_tcs_journal_id': self.company_data['default_journal_misc'].id,
        })
        self.period.action_compute_expected()
        self._import('tds', (
            'GSTIN of Deductor,Deductor\'s Name,Taxable Value,Integrated Tax,Central Tax,State/UT Tax\n'
            '%s,Partner A,"1,50,000",0,1500,1500\n'
            '%s,Partner A,150000,0,1500,1500\n'
            '29AAAAA0000A1Z5,Unknown Deductor,10000,200,0,0\n'
        ) % (self.partner_a.vat, self.partner_a.vat))
        tds = self._credit('tds').filtered('partner_id')
        self.assertAlmostEqual(tds.reported_taxable, 300000.0)
        self.assertAlmostEqual(tds.reported_total, 6000.0)
        self.assertEqual(tds.match_state, 'matched')
        unknown = self._credit('tds') - tds
        self.assertEqual(unknown.deductor_gstin, '29AAAAA0000A1Z5')
        self.assertEqual(unknown.match_state, 'reported_only')
        self.assertIn('Unknown Deductor', unknown.notes)
        self.assertEqual(self.period.mismatch_count, 1)

        self._import('tcs', 'GSTIN of E-commerce Operator,Net Value,Integrated Tax\n%s,80000,350\n' % self.partner_b.vat)
        tcs = self._credit('tcs')
        self.assertEqual(len(tcs), 1)
        self.assertEqual(tcs.match_state, 'mismatch')
        self.assertAlmostEqual(tcs.difference, -50.0)

        # Recomputing keeps what GSTR-2X reported.
        self.period.action_compute_expected()
        self.assertAlmostEqual(tds.reported_total, 6000.0)
        self.assertAlmostEqual(tcs.reported_igst, 350.0)

        self.period.action_accept_matched()
        self.assertEqual(tds.state, 'accepted')
        self.assertEqual(tcs.state, 'pending', 'A mismatch is not accepted in bulk.')
        self.assertEqual(tds.move_id.state, 'posted')
        debit = tds.move_id.line_ids.filtered(lambda l: l.account_id == account)
        self.assertAlmostEqual(debit.debit, 6000.0)
        credit = tds.move_id.line_ids - debit
        self.assertEqual(credit.account_id, self.partner_a.property_account_receivable_id)
        self.assertAlmostEqual(credit.credit, 6000.0)
        self.assertAlmostEqual(self.period.accepted_total, 6000.0)

        # A reported credit with no contact cannot be booked.
        with self.assertRaises(UserError):
            unknown.action_accept()
        unknown.action_reject()
        self.assertEqual(unknown.state, 'rejected')

        # Resetting needs the journal entry reversed first.
        with self.assertRaises(UserError):
            tds.action_reset()
        tds.move_id.button_draft()
        tds.action_reset()
        self.assertEqual(tds.state, 'pending')

        self.period.action_close()
        with self.assertRaises(UserError):
            self.period.action_compute_expected()

    def test_accept_without_account(self):
        self.period.action_compute_expected()
        tcs = self._credit('tcs')
        tcs.action_accept()
        self.assertEqual(tcs.state, 'accepted')
        self.assertFalse(tcs.move_id, 'No entry is booked when no account is set.')
        self.assertAlmostEqual(tcs.claim_total, 400.0)
