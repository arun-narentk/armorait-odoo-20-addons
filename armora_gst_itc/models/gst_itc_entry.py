# -*- coding: utf-8 -*-
from odoo import api, fields, models

HEADS = ('igst', 'cgst', 'sgst', 'cess')


class ArmoraGstItcEntry(models.Model):
    """A Rule 37 reversal (bill unpaid 180 days after its date) or the reclaim of
    such a reversal once the supplier is paid."""

    _name = 'armora.gst.itc.entry'
    _description = 'ITC Reversal or Reclaim'
    _order = 'reversal_date desc, id desc'

    ledger_id = fields.Many2one('armora.gst.itc.ledger', string='ITC Ledger', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='ledger_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='ledger_id.currency_id')
    gstin = fields.Char(related='ledger_id.gstin', store=True)
    entry_type = fields.Selection([
        ('rule37', 'Rule 37 reversal'),
        ('reclaim', 'Reclaim'),
    ], required=True, index=True)
    move_id = fields.Many2one('account.move', string='Vendor Bill', required=True, index=True, ondelete='restrict')
    partner_id = fields.Many2one(related='move_id.partner_id', store=True)
    invoice_date = fields.Date(related='move_id.invoice_date', store=True)
    reversal_date = fields.Date(string='Date', required=True, help='Last day of the month the entry belongs to.')
    reversal_id = fields.Many2one('armora.gst.itc.entry', string='Reversed Entry', index=True, ondelete='cascade',
                                  help='For a reclaim: the Rule 37 reversal it gives back.')
    bill_total = fields.Monetary(currency_field='currency_id')
    unpaid_amount = fields.Monetary(string='Unpaid on Day 180', currency_field='currency_id')
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
    cgst = fields.Monetary(string='CGST', currency_field='currency_id')
    sgst = fields.Monetary(string='SGST/UTGST', currency_field='currency_id')
    cess = fields.Monetary(string='Cess', currency_field='currency_id')
    total = fields.Monetary(compute='_compute_total', store=True, currency_field='currency_id')
    interest = fields.Monetary(currency_field='currency_id',
                               help='Interest at 18% a year from the month after the bill (when the credit was taken) to the reversal.')
    reclaim_ids = fields.One2many('armora.gst.itc.entry', 'reversal_id', string='Reclaims')

    @api.depends(*HEADS)
    def _compute_total(self):
        for entry in self:
            entry.total = sum(entry[head] for head in HEADS)

    def _remaining(self):
        """Part of a Rule 37 reversal that has not been reclaimed yet, by head."""
        self.ensure_one()
        return {head: self[head] - sum(self.reclaim_ids.mapped(head)) for head in HEADS}
