# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstCreditNoteReason(models.Model):
    _name = 'rn.gst.credit.note.reason'
    _description = 'GST Credit Note Reason'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    gst_credit = fields.Boolean(
        string='Reduces GST', default=True,
        help='A GST credit note under section 34 reduces the tax. A financial credit note (for example a '
             'discount not agreed before the sale) is only a commercial adjustment and must not carry GST.',
    )
    requires_original = fields.Boolean(string='Needs Original Invoice', default=True)
    description = fields.Text(translate=True)

    _rn_gst_credit_note_reason_code_uniq = models.Constraint('unique(code)', "The reason code must be unique.")
