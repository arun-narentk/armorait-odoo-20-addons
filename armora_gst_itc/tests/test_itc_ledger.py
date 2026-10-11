# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstItcLedger(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('armora_gst_itc.group_armora_gst_itc_manager').id)]
        if 'armora_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.armora_gst_block_post_on_error = False
        cls.exempt_sale = cls.env['account.chart.template'].ref('exempt_sale')

    def _post(self, move_type, amounts, taxes, invoice_date, treatments=None):
        move = self.init_invoice(
            move_type=move_type, partner=self.partner_a, amounts=amounts, taxes=taxes, invoice_date=invoice_date,
        )
        lines = move.invoice_line_ids
        lines.write({'l10n_in_hsn_code': '998314'})
        for line, treatment in zip(lines, treatments or []):
            line.armora_itc_treatment = treatment
        move.action_post()
        return move

    def _ledger(self, period, financial_year='2025-26'):
        ledger = self.env['armora.gst.itc.ledger'].create({
            'company_id': self.default_company.id,
            'financial_year': financial_year,
            'return_period': period,
        })
        ledger.action_compute()
        return ledger

    def test_itc_ledger_rules(self):
        self._post('out_invoice', [1000.0], self.sgst_sale_18, '2025-04-05')
        self._post('out_invoice', [250.0], self.exempt_sale, '2025-04-06')
        self._post('in_invoice', [1000.0, 1000.0], self.sgst_purchase_5, '2025-04-10', ['eligible', 'blocked'])
        self._post('in_invoice', [1000.0], self.sgst_purchase_5, '2025-04-12', ['common'])
        old_bill = self._post('in_invoice', [1000.0], self.sgst_purchase_5, '2025-01-10')

        april = self._ledger('04')
        self.assertEqual(len(april.bill_ids), 2)
        self.assertAlmostEqual(april.availed_cgst, 75.0)
        self.assertAlmostEqual(april.blocked_cgst, 25.0)
        self.assertAlmostEqual(april.rule42_ratio, 20.0)
        self.assertAlmostEqual(april.rule42_cgst, 5.0)
        self.assertAlmostEqual(april.net_cgst, 45.0)
        self.assertAlmostEqual(april.net_sgst, 45.0)
        self.assertFalse(april.entry_ids)
        self.assertAlmostEqual(april.closing_cgst, 45.0)

        # Day 180 of the January bill is 9 July and it is still unpaid.
        july = self._ledger('07')
        reversal = july.entry_ids
        self.assertEqual((reversal.entry_type, reversal.move_id), ('rule37', old_bill))
        self.assertAlmostEqual(reversal.cgst, 25.0)
        self.assertAlmostEqual(reversal.interest, 50.0 * 0.18 * 161 / 365, places=2)
        self.assertAlmostEqual(july.net_cgst, -25.0)
        self.assertEqual(july.previous_ledger_id, april)
        self.assertAlmostEqual(july.opening_cgst, 45.0)
        self.assertAlmostEqual(july.closing_cgst, 20.0)

        # The supplier is paid in August: the reversal is reclaimed in full.
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=old_bill.ids,
        ).create({'payment_date': '2025-08-05'})._create_payments()
        august = self._ledger('08')
        reclaim = august.entry_ids
        self.assertEqual((reclaim.entry_type, reclaim.reversal_id), ('reclaim', reversal))
        self.assertAlmostEqual(reclaim.cgst, 25.0)
        self.assertAlmostEqual(august.reclaimed_cgst, 25.0)
        self.assertAlmostEqual(august.closing_cgst, 45.0)
        self.assertFalse(any(reversal._remaining().values()))

        # July cannot be computed again while August reclaims its reversal.
        with self.assertRaises(UserError):
            july.action_compute()
        # Computing August again does not reclaim twice.
        august.action_compute()
        self.assertAlmostEqual(august.reclaimed_cgst, 25.0)

        april.action_lock()
        with self.assertRaises(UserError):
            april.action_compute()

    def test_gstr3b_takes_ledger(self):
        if 'armora.gst.3b' not in self.env:
            self.skipTest('Armora GST GSTR-3B is not installed.')
        self._post('out_invoice', [1000.0], self.sgst_sale_18, '2025-04-05')
        self._post('out_invoice', [250.0], self.exempt_sale, '2025-04-06')
        self._post('in_invoice', [1000.0, 1000.0], self.sgst_purchase_5, '2025-04-10', ['eligible', 'blocked'])
        self._post('in_invoice', [1000.0], self.sgst_purchase_5, '2025-04-12', ['common'])
        self._ledger('04')
        gstr3b = self.env['armora.gst.3b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'period_start': '2025-04-01',
            'period_end': '2025-04-30',
            'due_date': '2025-05-20',
            'payment_date': '2025-05-20',
        })
        gstr3b.action_fill_from_books()
        self.assertAlmostEqual(gstr3b.t4a5_cgst, 75.0)
        self.assertAlmostEqual(gstr3b.t4b1_cgst, 30.0)
        self.assertAlmostEqual(gstr3b.t4c_cgst, 45.0)
        self.assertAlmostEqual(gstr3b.itc_available_cgst, 45.0)
