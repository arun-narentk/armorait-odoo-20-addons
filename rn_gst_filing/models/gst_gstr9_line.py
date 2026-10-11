# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

from .gstr9_rows import PARTS

AMOUNT_FIELDS = ('value', 'cash', 'igst', 'cgst', 'sgst', 'cess')


class RnGstGstr9Line(models.Model):
    _name = 'rn.gst.gstr9.line'
    _description = 'GSTR-9 Row'
    _order = 'sequence, id'

    gstr9_id = fields.Many2one('rn.gst.gstr9', string='GSTR-9', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='gstr9_id.company_id', store=True)
    currency_id = fields.Many2one(related='gstr9_id.currency_id')
    sequence = fields.Integer()
    code = fields.Char(required=True, readonly=True)
    part = fields.Selection(PARTS, required=True, readonly=True)
    table = fields.Char(readonly=True)
    label = fields.Char(string='Details', required=True, readonly=True)
    kind = fields.Selection([
        ('tax', 'Value and tax'),
        ('value', 'Value only'),
        ('itc', 'Tax only'),
        ('pay', 'Tax payable and paid'),
    ], required=True, readonly=True)
    source = fields.Selection([
        ('books', 'Books'),
        ('gstr3b', 'GSTR-3B'),
        ('gstr2b', 'GSTR-2B'),
        ('computed', 'Total'),
        ('manual', 'Manual'),
    ], required=True, readonly=True)
    value = fields.Monetary(string='Taxable Value / Payable', currency_field='currency_id')
    cash = fields.Monetary(string='Paid in Cash', currency_field='currency_id')
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
    cgst = fields.Monetary(string='CGST', currency_field='currency_id')
    sgst = fields.Monetary(string='SGST/UTGST', currency_field='currency_id')
    cess = fields.Monetary(string='Cess', currency_field='currency_id')

    def write(self, vals):
        if self.gstr9_id.filtered(lambda r: r.state == 'filed') and not self.env.su:
            raise UserError(_('A filed GSTR-9 is read-only. Reset it to draft first.'))
        res = super().write(vals)
        if set(vals) & set(AMOUNT_FIELDS) and not self.env.context.get('rn_gstr9_totals'):
            self.gstr9_id._rn_recompute_totals()
        return res


class RnGstGstr9Hsn(models.Model):
    _name = 'rn.gst.gstr9.hsn'
    _description = 'GSTR-9 HSN Summary Line'
    _order = 'direction, hsn_code, rate'

    gstr9_id = fields.Many2one('rn.gst.gstr9', string='GSTR-9', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='gstr9_id.company_id', store=True)
    currency_id = fields.Many2one(related='gstr9_id.currency_id')
    direction = fields.Selection([
        ('outward', 'Outward (Table 17)'),
        ('inward', 'Inward (Table 18)'),
    ], required=True)
    hsn_code = fields.Char(string='HSN/SAC', required=True)
    uqc = fields.Char(string='UQC')
    quantity = fields.Float(digits='Product Unit of Measure')
    taxable_value = fields.Monetary(currency_field='currency_id')
    rate = fields.Float(string='Rate %', digits=(16, 2))
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
    cgst = fields.Monetary(string='CGST', currency_field='currency_id')
    sgst = fields.Monetary(string='SGST/UTGST', currency_field='currency_id')
    cess = fields.Monetary(string='Cess', currency_field='currency_id')
