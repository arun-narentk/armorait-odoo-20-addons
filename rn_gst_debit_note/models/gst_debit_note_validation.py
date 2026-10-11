# -*- coding: utf-8 -*-
"""GST debit-note validation finding (skeleton).

Tracks compliance outcomes for moves with debit_origin_id.
Additional liability validation lands in Prompts 4–10.
"""

from odoo import fields, models


class RnGstDebitNoteValidation(models.Model):
    _name = 'rn.gst.debit.note.validation'
    _description = 'Armora GST Debit Note Validation'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Debit Note',
        index=True,
        check_company=True,
        help='Expected to be an account.move with debit_origin_id set.',
    )
    reason_id = fields.Many2one('rn.gst.debit.note.reason', index=True)
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('pass', 'Pass'),
            ('warning', 'Warning'),
            ('blocked', 'Blocked'),
        ],
        default='pending',
        required=True,
        index=True,
    )
    severity = fields.Selection(
        selection=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        default='info',
        required=True,
    )
    note = fields.Text()
    active = fields.Boolean(default=True)
