# -*- coding: utf-8 -*-
from odoo import fields, models


class ArmoraGst3bInterstateLine(models.Model):
    """GSTR-3B Table 3.2: inter-state supplies to unregistered persons,
    composition taxable persons and UIN holders, by place of supply."""

    _name = 'armora.gst.3b.interstate.line'
    _description = 'GSTR-3B Inter-State Supply Line'
    _order = 'supply_type, state_id'

    filing_id = fields.Many2one('armora.gst.3b', string='GSTR-3B', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='filing_id.company_id', store=True)
    currency_id = fields.Many2one(related='filing_id.currency_id')
    supply_type = fields.Selection([
        ('unregistered', 'Unregistered Persons'),
        ('composition', 'Composition Taxable Persons'),
        ('uin', 'UIN Holders'),
    ], required=True)
    state_id = fields.Many2one('res.country.state', string='Place of Supply', required=True)
    taxable_value = fields.Monetary(currency_field='currency_id')
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
