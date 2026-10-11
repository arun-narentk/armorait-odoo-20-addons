# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import RnGstFilingTestCommon


@tagged('post_install', '-at_install')
class TestRnGstClassification(RnGstFilingTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Classification = cls.env['rn.gst.classification']
        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'
        cls.product_a.l10n_in_hsn_code = '998314'
        cls.consumer = cls.env['res.partner'].create({
            'name': 'B2C Customer',
            'country_id': cls.country_in.id,
            'state_id': cls.state_in_mh.id,
            'l10n_in_gst_treatment': 'consumer',
        })

    def _post_invoice(self, partner, taxes, amount=1000.0, move_type='out_invoice', invoice_date='2025-04-10'):
        return self.init_invoice(
            move_type=move_type,
            partner=partner,
            amounts=[amount],
            taxes=taxes,
            post=True,
            invoice_date=invoice_date,
        )

    def test_intrastate_b2b(self):
        move = self._post_invoice(self.partner_a, self.sgst_sale_18)
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['gst_table'], 'b2b')
        self.assertEqual(result['supply_type'], 'b2b')
        self.assertEqual(result['tax_type'], 'cgst_sgst')

    def test_interstate_b2b(self):
        move = self._post_invoice(self.partner_b, self.igst_sale_18)
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['gst_table'], 'b2b')
        self.assertEqual(result['supply_type'], 'b2b')

    def test_b2cs(self):
        move = self._post_invoice(self.consumer, self.igst_sale_18, amount=1000)
        move.l10n_in_state_id = self.state_in_gj
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['gst_table'], 'b2cs')
        self.assertEqual(result['supply_type'], 'b2cs')

    def test_b2cl(self):
        move = self._post_invoice(self.consumer, self.igst_sale_18, amount=300000)
        move.l10n_in_state_id = self.state_in_mh
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['gst_table'], 'b2cl')
        self.assertEqual(result['supply_type'], 'b2cl')

    def test_export(self):
        move = self._post_invoice(self.partner_foreign, self.igst_sale_18)
        vals = {
            'l10n_in_gst_treatment': 'overseas',
            'l10n_in_shipping_bill_number': 'SB001',
            'l10n_in_shipping_bill_date': move.invoice_date,
        }
        port = self.env['l10n_in.port.code'].search([], limit=1)
        if port:
            vals['l10n_in_shipping_port_code_id'] = port.id
        move.write(vals)
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['gst_table'], 'exp')
        self.assertEqual(result['supply_type'], 'export')

    def test_sez(self):
        partner = self.partner_b.copy({'name': 'SEZ Partner', 'l10n_in_gst_treatment': 'special_economic_zone'})
        move = self._post_invoice(partner, self.igst_sale_18)
        move.l10n_in_gst_treatment = 'special_economic_zone'
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertIn(result['gst_table'], ('b2b', 'exp'))

    def test_deemed_export(self):
        partner = self.partner_a.copy({'name': 'Deemed', 'l10n_in_gst_treatment': 'deemed_export'})
        move = self._post_invoice(partner, self.igst_sale_18)
        move.l10n_in_gst_treatment = 'deemed_export'
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertEqual(result['supply_type'], 'deemed_export')

    def test_credit_note_cdnr(self):
        invoice = self._post_invoice(self.partner_a, self.sgst_sale_18)
        reversal = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'reason': 'Test credit',
            'journal_id': invoice.journal_id.id,
        })
        reversal.refund_moves()
        credit = invoice.reversal_move_ids[:1]
        self.assertTrue(credit)
        line = credit.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(credit, line)
        self.assertEqual(result['gst_table'], 'cdnr')
        self.assertEqual(result['document_type'], 'credit_note')

    def test_missing_pos_error(self):
        move = self._post_invoice(self.partner_a, self.sgst_sale_18)
        move.l10n_in_state_id = False
        line = move.invoice_line_ids.filtered(lambda l: l.display_type in (False, 'product'))[:1]
        result = self.Classification.classify_move_line(move, line)
        self.assertTrue(any('Place of supply' in e for e in result['errors']))
