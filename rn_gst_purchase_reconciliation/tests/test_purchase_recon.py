# -*- coding: utf-8 -*-
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstPurchaseRecon(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [
            (4, cls.env.ref('rn_gst_purchase_reconciliation.group_rn_gst_purchase_recon_user').id),
            (4, cls.env.ref('purchase.group_purchase_manager').id),
        ]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.today = fields.Date.today()
        cls.product = cls.env['product.product'].create({
            'name': 'Steel Rack', 'type': 'consu', 'is_storable': True, 'l10n_in_hsn_code': '94032090',
            'standard_price': 100.0,
        }) if 'is_storable' in cls.env['product.product']._fields else cls.env['product.product'].create({
            'name': 'Steel Rack', 'type': 'consu', 'l10n_in_hsn_code': '94032090', 'standard_price': 100.0,
        })
        cls.sgst_purchase_18 = cls.env['account.chart.template'].ref('sgst_purchase_18')

    def _po(self, qty=10.0, price=100.0):
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product.id, 'product_qty': qty, 'price_unit': price,
                'tax_ids': [Command.set(self.sgst_purchase_5.ids)],
            })],
        })
        po.button_confirm()
        return po

    def _receive(self, po):
        for picking in po.picking_ids:
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.move_ids.picked = True
            picking.button_validate()

    def _bill(self, po, ref='SUP/001'):
        po.action_create_invoice()
        bill = po.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]
        bill.write({'ref': ref, 'invoice_date': self.today})
        return bill

    def _recon(self):
        recon = self.env['rn.gst.purchase.recon'].create({'date_from': self.today, 'date_to': self.today})
        recon.action_run()
        return recon

    def _codes(self, recon, bill=None):
        lines = recon.line_ids.filtered(lambda l: not bill or l.move_id == bill)
        return set(lines.mapped('code'))

    def test_clean_bill(self):
        po = self._po()
        if po.picking_ids:
            self._receive(po)
        else:
            po.order_line.qty_received = 10.0
        bill = self._bill(po)
        bill.action_post()
        recon = self._recon()
        self.assertEqual(recon.bill_count, 1)
        self.assertFalse(self._codes(recon, bill))

    def test_over_billed_price_and_tax(self):
        po = self._po()
        bill = self._bill(po)
        line = bill.invoice_line_ids
        line.write({'quantity': 10.0, 'price_unit': 120.0, 'tax_ids': [Command.set(self.sgst_purchase_18.ids)]})
        bill.action_post()
        recon = self._recon()
        self.assertEqual(self._codes(recon, bill), {'over_billed', 'price', 'tax'})
        over = recon.line_ids.filtered(lambda l: l.code == 'over_billed')
        self.assertEqual(over.severity, 'error')
        self.assertEqual(over.difference, 1000.0)
        self.assertEqual(recon.line_ids.filtered(lambda l: l.code == 'price').difference, 200.0)

    def test_duplicate_and_missing_ref(self):
        first = self._bill(self._po(), ref='INV-77')
        first.action_post()
        second = self._bill(self._po(), ref='inv 77')
        second.action_post()
        third = self._bill(self._po(), ref=False)
        third.action_post()
        recon = self._recon()
        self.assertIn('duplicate', self._codes(recon, second))
        self.assertNotIn('duplicate', self._codes(recon, first))
        self.assertIn('no_ref', self._codes(recon, third))

    def test_hsn_and_no_po(self):
        bill = self.init_invoice('in_invoice', partner=self.partner_a, products=self.product,
                                 taxes=self.sgst_purchase_5, invoice_date=self.today)
        bill.write({'ref': 'X-1'})
        bill.invoice_line_ids.l10n_in_hsn_code = '94031000'
        bill.action_post()
        recon = self._recon()
        self.assertEqual(self._codes(recon, bill), {'hsn', 'no_po'})

    def test_review_and_ignore_kept_on_rerun(self):
        bill = self._bill(self._po(), ref=False)
        bill.action_post()
        recon = self._recon()
        line = recon.line_ids.filtered(lambda l: l.code == 'no_ref')
        with self.assertRaises(UserError):
            line.action_ignore()
        line.note = 'Supplier sends handwritten bills'
        line.action_ignore()
        self.assertEqual(recon.open_count, len(recon.line_ids) - 1)
        recon.action_run()
        again = recon.line_ids.filtered(lambda l: l.code == 'no_ref')
        self.assertEqual((again.state, again.note), ('ignored', 'Supplier sends handwritten bills'))
