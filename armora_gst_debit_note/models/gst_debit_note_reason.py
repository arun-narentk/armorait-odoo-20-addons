# -*- coding: utf-8 -*-
"""GST debit-note reason master (skeleton).

Reason-driven validation requirements land in Prompt 5.
Do not reuse credit-note reason codes blindly.
"""

from odoo import fields, models


class ArmoraGstDebitNoteReason(models.Model):
    _name = 'armora.gst.debit.note.reason'
    _description = 'Armora GST Debit Note Reason'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    require_original_invoice = fields.Boolean(
        default=True,
        help='When set, validation will require debit_origin_id (implemented later).',
    )
    require_quantity = fields.Boolean(
        default=False,
        help='Debit notes usually add value/tax; quantity rules are optional per reason.',
    )
    gst_applicable = fields.Boolean(
        default=True,
        help='Unset for commercial adjustments that must not be treated as GST DBN.',
    )

    _code_uniq = models.Constraint(
        'unique(code)',
        "Debit note reason code must be unique.",
    )
