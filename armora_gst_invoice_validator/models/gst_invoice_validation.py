# -*- coding: utf-8 -*-
import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.sql_db import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from .gst_validation_constants import VALIDATION_RUN_STATE_SELECTION

_logger = logging.getLogger(__name__)

# Map legacy error_type values from armora.gst.invoice.validator to categories.
_ERROR_TYPE_CATEGORY = {
    'missing_gstin': 'GSTIN',
    'invalid_gstin': 'GSTIN',
    'missing_place_of_supply': 'PLACE_OF_SUPPLY',
    'pos_gstin_mismatch': 'PLACE_OF_SUPPLY',
    'missing_hsn': 'HSN',
    'missing_sac': 'SAC',
    'tax_type_mismatch': 'TAX',
    'tax_mismatch': 'TAX',
    'invalid_tax_rate': 'GST_RATE',
    'invoice_series': 'DOCUMENT',
    'missing_invoice_number': 'DOCUMENT',
    'invalid_invoice_date': 'DOCUMENT',
    'duplicate_invoice': 'DUPLICATE',
    'missing_cdn_reference': 'CREDIT_NOTE',
    'missing_export_info': 'EXPORT',
    'rcm_mismatch': 'REVERSE_CHARGE',
    'einvoice_eligibility': 'E_INVOICE_PREREQUISITE',
    'einvoice_pending': 'E_INVOICE_PREREQUISITE',
    'einvoice_failed': 'E_INVOICE_PREREQUISITE',
    'ewaybill_pending': 'EWAYBILL_PREREQUISITE',
    'cancelled_invoice': 'INVOICE',
    'missing_tax_configuration': 'TAX',
    'other': 'ACCOUNTING',
}

_ERROR_TYPE_FIELD = {
    'missing_gstin': 'l10n_in_gstin',
    'invalid_gstin': 'l10n_in_gstin',
    'missing_place_of_supply': 'l10n_in_state_id',
    'pos_gstin_mismatch': 'l10n_in_state_id',
    'missing_hsn': 'l10n_in_hsn_code',
    'missing_sac': 'l10n_in_hsn_code',
    'invoice_series': 'name',
    'missing_invoice_number': 'name',
    'invalid_invoice_date': 'invoice_date',
    'missing_cdn_reference': 'reversed_entry_id',
    'missing_export_info': 'l10n_in_shipping_bill_number',
    'tax_type_mismatch': 'tax_ids',
    'tax_mismatch': 'amount_tax',
    'missing_tax_configuration': 'tax_ids',
    'rcm_mismatch': 'tax_ids',
}

_GST_MOVE_TYPES = (
    'out_invoice',
    'out_refund',
    'in_invoice',
    'in_refund',
)


class ArmoraGstInvoiceValidation(models.Model):
    """One GST invoice validation execution (single invoice or batch).

    Runs the shared invoice validator engine, stores auditable results on
    this run, and optionally refreshes per-move issue rows. Does not change
    invoice taxes, amounts, GSTIN, or other accounting values.
    """

    _name = 'armora.gst.invoice.validation'
    _description = 'GST Invoice Validation Run'
    _order = 'validation_date desc, id desc'

    name = fields.Char(required=True, copy=False, default='New', index=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    validation_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    validated_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        index=True,
    )
    invoice_ids = fields.Many2many(
        'account.move',
        'armora_gst_invoice_validation_move_rel',
        'validation_id',
        'move_id',
        string='Invoices',
        domain="[('company_id', '=', company_id), ('move_type', 'in', ("
               "'out_invoice', 'out_refund', 'in_invoice', 'in_refund'"
               "))]",
    )
    result_ids = fields.One2many(
        'armora.gst.invoice.validation.line',
        'validation_id',
        string='Results',
        copy=False,
    )
    total_invoices = fields.Integer(compute='_compute_counts', store=True)
    valid_invoices = fields.Integer(compute='_compute_counts', store=True)
    error_count = fields.Integer(compute='_compute_counts', store=True)
    warning_count = fields.Integer(compute='_compute_counts', store=True)
    info_count = fields.Integer(compute='_compute_counts', store=True)
    blocking_count = fields.Integer(compute='_compute_counts', store=True)
    state = fields.Selection(
        selection=VALIDATION_RUN_STATE_SELECTION,
        default='draft',
        required=True,
        index=True,
        copy=False,
        string='Status',
    )
    duration = fields.Float(string='Duration (s)', copy=False)
    notes = fields.Text()
    sync_move_issues = fields.Boolean(
        string='Refresh Invoice Issues',
        default=True,
        help='When enabled, also refreshes per-invoice GST issue rows used on '
             'the invoice form. Accounting amounts and GST fields are never changed.',
    )

    @api.depends(
        'invoice_ids',
        'result_ids',
        'result_ids.severity',
        'result_ids.blocking',
        'result_ids.invoice_id',
    )
    def _compute_counts(self):
        for record in self:
            results = record.result_ids
            invoices = record.invoice_ids
            record.total_invoices = len(invoices)
            record.error_count = len(results.filtered(lambda r: r.severity == 'error'))
            record.warning_count = len(results.filtered(lambda r: r.severity == 'warning'))
            record.info_count = len(results.filtered(lambda r: r.severity == 'info'))
            record.blocking_count = len(results.filtered('blocking'))
            errored_moves = results.filtered(lambda r: r.severity == 'error').mapped('invoice_id')
            record.valid_invoices = len(invoices - errored_moves)

    @api.constrains('invoice_ids', 'company_id')
    def _check_invoice_company(self):
        for record in self:
            wrong = record.invoice_ids.filtered(
                lambda m: m.company_id != record.company_id
            )
            if wrong:
                raise ValidationError(
                    _('All documents on a validation run must belong to company %s.')
                    % record.company_id.display_name
                )
            bad_type = record.invoice_ids.filtered(
                lambda m: m.move_type not in _GST_MOVE_TYPES
            )
            if bad_type:
                raise ValidationError(
                    _('Validation runs only accept customer/vendor invoices and '
                      'credit notes.')
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'armora.gst.invoice.validation'
                ) or 'New'
        return super().create(vals_list)

    @api.model
    def create_for_invoices(self, invoices, sync_move_issues=True, notes=False):
        """Create a draft run for invoices and execute it immediately."""
        invoices = invoices.exists()
        if not invoices:
            raise UserError(_('Select at least one invoice to validate.'))
        companies = invoices.mapped('company_id')
        if len(companies) != 1:
            raise UserError(_('Batch validation must use documents from one company.'))
        run = self.create({
            'company_id': companies.id,
            'invoice_ids': [(6, 0, invoices.ids)],
            'sync_move_issues': sync_move_issues,
            'notes': notes or False,
        })
        run.action_run_validation()
        return run

    def action_run_validation(self):
        for run in self:
            run._run_validation()
        return True

    def action_rerun_validation(self):
        """Clear this run's results and execute again.

        Other historical runs are left untouched.
        """
        for run in self:
            if run.state == 'running':
                raise UserError(_('Validation %s is already running.') % run.display_name)
            run.result_ids.unlink()
            run.write({
                'state': 'draft',
                'duration': 0.0,
                'validation_date': fields.Datetime.now(),
                'validated_by': self.env.user.id,
            })
            run._run_validation()
        return True

    def action_cancel(self):
        for run in self:
            if run.state == 'running':
                raise UserError(_('Cannot cancel a running validation.'))
            run.state = 'cancelled'
        return True

    def action_view_errors(self):
        self.ensure_one()
        return self._action_view_results([('severity', '=', 'error')])

    def action_view_warnings(self):
        self.ensure_one()
        return self._action_view_results([('severity', '=', 'warning')])

    def action_mark_reviewed(self):
        self.ensure_one()
        open_results = self.result_ids.filtered(lambda r: r.status == 'open')
        open_results.write({
            'status': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_at': fields.Datetime.now(),
        })
        return True

    def _action_view_results(self, extra_domain):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Validation Results'),
            'res_model': 'armora.gst.invoice.validation.line',
            'view_mode': 'list,form',
            'domain': [('validation_id', '=', self.id)] + list(extra_domain),
            'context': {'default_validation_id': self.id},
        }

    def _run_validation(self):
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('Cancelled validation runs cannot be executed.'))
        if not self.invoice_ids:
            raise UserError(_('Add at least one invoice before running validation.'))

        self.write({
            'state': 'running',
            'validation_date': fields.Datetime.now(),
            'validated_by': self.env.user.id,
        })
        # Re-run safety: never keep stale results on this run.
        self.result_ids.unlink()

        started = time.monotonic()
        Line = self.env['armora.gst.invoice.validation.line']
        Validator = self.env['armora.gst.invoice.validator']
        result_vals = []
        seen_keys = set()

        try:
            # Savepoint: a crash undoes only this run's partial results, so the
            # 'failed' state and error note below are kept instead of being
            # rolled back with the whole request.
            with self.env.cr.savepoint():
                invoices = self.invoice_ids.filtered(
                    lambda m: m.company_id == self.company_id
                )
                # Prefetch related data for the batch.
                invoices.mapped('invoice_line_ids.tax_ids')
                invoices.mapped('partner_id')
                invoices.mapped('l10n_in_state_id')

                for move in invoices:
                    engine = Validator.validate_move(
                        move,
                        persist=bool(self.sync_move_issues),
                    )
                    for issue in engine.get('issues') or []:
                        vals = self._issue_to_result_vals(move, issue)
                        key = vals['dedupe_key']
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        result_vals.append(vals)

                if result_vals:
                    Line.create(result_vals)

            self.write({
                'state': 'completed',
                'duration': time.monotonic() - started,
            })
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # Let the request retry instead of recording a failed run.
            raise
        except Exception as err:
            _logger.exception('GST invoice validation run %s failed', self.name)
            self.invalidate_recordset()
            self.write({
                'state': 'failed',
                'duration': time.monotonic() - started,
                'notes': '\n'.join(filter(None, [
                    self.notes,
                    _('Run failed: %s', err),
                ])),
            })

    def _issue_to_result_vals(self, move, issue):
        """Convert a legacy validator issue dict into a run result vals dict."""
        self.ensure_one()
        error_type = issue.get('error_type') or 'other'
        severity = issue.get('severity') or 'error'
        if severity == 'review':
            severity = 'info'
        if severity not in ('error', 'warning', 'info'):
            severity = 'info'

        move_line_id = issue.get('move_line_id') or False
        rule_code = (error_type or 'other').upper()
        dedupe_key = '%s|%s|%s' % (move.id, rule_code, move_line_id or 0)

        message = issue.get('message') or _('Validation issue.')
        hint = issue.get('hint') or False
        if hint:
            message = '%s\n%s' % (message, hint)

        return {
            'validation_id': self.id,
            'invoice_id': move.id,
            'move_line_id': move_line_id,
            'partner_id': move.partner_id.id,
            'category': _ERROR_TYPE_CATEGORY.get(error_type, 'ACCOUNTING'),
            'rule_code': rule_code,
            'severity': severity,
            'field_name': _ERROR_TYPE_FIELD.get(error_type, False),
            'message': message,
            'expected_value': False,
            'actual_value': False,
            'blocking': severity == 'error',
            'status': 'open',
            'dedupe_key': dedupe_key,
            'created_at': fields.Datetime.now(),
        }
