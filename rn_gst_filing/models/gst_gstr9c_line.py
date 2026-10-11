# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

from .gstr9c_rows import PARTS

AMOUNT_FIELDS = ('value', 'igst', 'cgst', 'sgst', 'cess')


class RnGstGstr9cLine(models.Model):
    _name = 'rn.gst.gstr9c.line'
    _description = 'GSTR-9C Row'
    _order = 'sequence, id'

    gstr9c_id = fields.Many2one('rn.gst.gstr9c', string='GSTR-9C', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='gstr9c_id.company_id', store=True)
    currency_id = fields.Many2one(related='gstr9c_id.currency_id')
    sequence = fields.Integer()
    code = fields.Char(required=True, readonly=True)
    part = fields.Selection(PARTS, required=True, readonly=True)
    table = fields.Char(readonly=True)
    label = fields.Char(string='Details', required=True, readonly=True)
    kind = fields.Selection([
        ('tax', 'Value and tax'),
        ('value', 'Value only'),
        ('itc', 'Tax only'),
    ], required=True, readonly=True)
    source = fields.Selection([
        ('books', 'Books'),
        ('gstr9', 'GSTR-9'),
        ('computed', 'Total'),
        ('manual', 'Manual'),
    ], required=True, readonly=True)
    value = fields.Monetary(string='Amount', currency_field='currency_id')
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
    cgst = fields.Monetary(string='CGST', currency_field='currency_id')
    sgst = fields.Monetary(string='SGST/UTGST', currency_field='currency_id')
    cess = fields.Monetary(string='Cess', currency_field='currency_id')

    def write(self, vals):
        if self.gstr9c_id.filtered(lambda r: r.state == 'filed') and not self.env.su:
            raise UserError(_('A filed GSTR-9C is read-only. Reset it to draft first.'))
        res = super().write(vals)
        if set(vals) & set(AMOUNT_FIELDS) and not self.env.context.get('rn_gstr9c_totals'):
            self.gstr9c_id._rn_recompute_totals()
        return res


class RnGstGstr9cRate(models.Model):
    """Table 9: tax liability as per books, one line per tax rate."""

    _name = 'rn.gst.gstr9c.rate'
    _description = 'GSTR-9C Rate-wise Liability'
    _order = 'rate'

    gstr9c_id = fields.Many2one('rn.gst.gstr9c', string='GSTR-9C', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='gstr9c_id.company_id', store=True)
    currency_id = fields.Many2one(related='gstr9c_id.currency_id')
    rate = fields.Float(string='Rate %', digits=(16, 2), required=True)
    taxable_value = fields.Monetary(currency_field='currency_id')
    igst = fields.Monetary(string='IGST', currency_field='currency_id')
    cgst = fields.Monetary(string='CGST', currency_field='currency_id')
    sgst = fields.Monetary(string='SGST/UTGST', currency_field='currency_id')
    cess = fields.Monetary(string='Cess', currency_field='currency_id')


class RnGstGstr9cExpense(models.Model):
    """Table 14: ITC on expenses as per books, one line per expense account."""

    _name = 'rn.gst.gstr9c.expense'
    _description = 'GSTR-9C Expense-wise ITC'
    _order = 'itc_amount desc, id'

    gstr9c_id = fields.Many2one('rn.gst.gstr9c', string='GSTR-9C', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='gstr9c_id.company_id', store=True)
    currency_id = fields.Many2one(related='gstr9c_id.currency_id')
    account_id = fields.Many2one('account.account', string='Expense Account')
    name = fields.Char(string='Description', required=True)
    expense_value = fields.Monetary(string='Value', currency_field='currency_id')
    itc_amount = fields.Monetary(string='Eligible ITC', currency_field='currency_id')
