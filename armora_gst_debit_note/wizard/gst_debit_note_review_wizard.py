# -*- coding: utf-8 -*-
"""GST debit note review wizard (skeleton).

Shows original vs additional liability summary in Prompt 18.
Must never modify accounting data when opened.
"""

from odoo import fields, models


class ArmoraGstDebitNoteReviewWizard(models.TransientModel):
    _name = 'armora.gst.debit.note.review.wizard'
    _description = 'Armora GST Debit Note Review Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Debit Note',
        check_company=True,
    )
    note = fields.Text(
        readonly=True,
        default=(
            'Review will compare original invoice vs debit note additional taxable value and tax. '
            'Opening this wizard must not change accounting data. Engine lands in later prompts.'
        ),
    )

    def action_close(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
