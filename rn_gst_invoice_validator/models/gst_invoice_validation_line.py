# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .gst_validation_constants import (
    VALIDATION_CATEGORY_SELECTION,
    VALIDATION_RESULT_STATUS_SELECTION,
    VALIDATION_SEVERITY_SELECTION,
)


class RnGstInvoiceValidationLine(models.Model):
    """One GST validation finding for an invoice inside a validation run."""

    _name = 'rn.gst.invoice.validation.line'
    _description = 'GST Invoice Validation Result'
    _order = 'severity, category, id'

    validation_id = fields.Many2one(
        'rn.gst.invoice.validation',
        required=True,
        ondelete='cascade',
        index=True,
    )
    invoice_id = fields.Many2one(
        'account.move',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        ondelete='set null',
        index=True,
    )
    company_id = fields.Many2one(
        related='validation_id.company_id',
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        index=True,
    )
    category = fields.Selection(
        selection=VALIDATION_CATEGORY_SELECTION,
        required=True,
        index=True,
    )
    rule_code = fields.Char(required=True, index=True)
    severity = fields.Selection(
        selection=VALIDATION_SEVERITY_SELECTION,
        required=True,
        default='error',
        index=True,
    )
    field_name = fields.Char()
    message = fields.Text(required=True)
    expected_value = fields.Char()
    actual_value = fields.Char()
    blocking = fields.Boolean(default=False, index=True)
    status = fields.Selection(
        selection=VALIDATION_RESULT_STATUS_SELECTION,
        default='open',
        required=True,
        index=True,
    )
    resolution_notes = fields.Text()
    resolved_by = fields.Many2one('res.users')
    resolved_at = fields.Datetime()
    created_at = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    dedupe_key = fields.Char(
        required=True,
        index=True,
        help='Stable key for uniqueness inside one validation run.',
    )

    _uniq_validation_dedupe_key = models.Constraint(
        'unique(validation_id, dedupe_key)',
        "Duplicate validation result for the same run and rule.",
    )

    @api.depends('rule_code', 'invoice_id', 'severity')
    def _compute_display_name(self):
        for record in self:
            invoice = record.invoice_id.display_name or ''
            record.display_name = '%s [%s] %s' % (
                record.rule_code or 'RULE',
                record.severity or '',
                invoice,
            )
