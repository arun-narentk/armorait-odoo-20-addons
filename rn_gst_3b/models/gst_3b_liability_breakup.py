# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RnGst3bLiabilityBreakup(models.Model):
    """Previous-period supplies reported in the current GSTR-3B period."""

    _name = 'rn.gst.3b.liability.breakup'
    _description = 'GSTR-3B Tax Liability Breakup'
    _order = 'source_period, document_date, id'

    filing_id = fields.Many2one(
        'rn.gst.3b',
        string='GSTR-3B Filing',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='filing_id.company_id', store=True)
    source_period = fields.Char(required=True, help='YYYYMM of the original supply period')
    reporting_period = fields.Char(required=True, help='YYYYMM of the GSTR-3B reporting period')
    document_id = fields.Many2one('account.move', string='Document', ondelete='set null')
    document_name = fields.Char()
    document_date = fields.Date()
    taxable_value = fields.Monetary(currency_field='currency_id')
    igst = fields.Monetary(currency_field='currency_id')
    cgst = fields.Monetary(currency_field='currency_id')
    sgst = fields.Monetary(currency_field='currency_id')
    cess = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='filing_id.currency_id')
    source_return = fields.Selection(
        selection=[
            ('gstr1', 'GSTR-1'),
            ('gstr1a', 'GSTR-1A'),
            ('iff', 'IFF'),
        ],
        required=True,
        default='gstr1',
    )
    source_table = fields.Char(help='e.g. B2B, CDNR, EXP')

    @api.constrains('source_period', 'reporting_period')
    def _check_periods(self):
        for line in self:
            if line.source_period and line.reporting_period and line.source_period >= line.reporting_period:
                raise ValidationError(_(
                    'Liability breakup source_period must be earlier than reporting_period '
                    '(previous-period supplies only).'
                ))
