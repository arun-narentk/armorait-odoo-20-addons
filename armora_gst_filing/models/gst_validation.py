# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class ArmoraGstValidationResult(models.Model):
    _name = 'armora.gst.validation.result'
    _description = 'GST Filing Validation Result'
    _order = 'severity, error_type, id'

    filing_id = fields.Many2one(
        'armora.gst.filing',
        required=True,
        ondelete='cascade',
        index=True,
    )
    line_id = fields.Many2one('armora.gst.filing.line', ondelete='cascade', index=True)
    move_id = fields.Many2one('account.move', string='Invoice', index=True)
    partner_id = fields.Many2one('res.partner', index=True)
    company_id = fields.Many2one(related='filing_id.company_id', store=True, index=True)

    severity = fields.Selection([
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ], required=True, default='error', index=True)
    error_type = fields.Selection([
        ('missing_gstin', 'Missing GSTIN'),
        ('invalid_gstin', 'Invalid GSTIN'),
        ('missing_hsn', 'Missing HSN'),
        ('missing_sac', 'Missing SAC'),
        ('missing_place_of_supply', 'Missing Place of Supply'),
        ('invalid_tax_rate', 'Invalid Tax Rate'),
        ('tax_mismatch', 'Tax Calculation Mismatch'),
        ('duplicate_invoice', 'Duplicate Invoice'),
        ('missing_invoice_number', 'Missing Invoice Number'),
        ('invalid_invoice_date', 'Invalid Invoice Date'),
        ('missing_export_info', 'Missing Export Information'),
        ('missing_cdn_reference', 'Missing Credit/Debit Note Reference'),
        ('cancelled_invoice', 'Cancelled Invoice'),
        ('missing_tax_configuration', 'Missing Tax Configuration'),
        ('reconciliation', 'Reconciliation Difference'),
        ('negative_taxable', 'Negative Taxable Value'),
        ('other', 'Other'),
    ], required=True, default='other', index=True)
    message = fields.Text(required=True)
    hint = fields.Text(
        string='How to Fix',
        help='Plain-language guidance. Prefer fixing the source invoice, then regenerate the filing snapshot.',
    )

    def action_open_invoice(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('This validation issue is not linked to an invoice.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_filing_line(self):
        self.ensure_one()
        if not self.line_id:
            raise UserError(_('This validation issue is not linked to a filing line.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('GST Filing Line'),
            'res_model': 'armora.gst.filing.line',
            'res_id': self.line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_partner(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('This validation issue is not linked to a partner.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner'),
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ArmoraGstFilingValidation(models.AbstractModel):
    """Filing-period validation engine.

    Named ``armora.gst.filing.validation`` so it does not collide with the shared
    pre-API validator ``armora.gst.validation`` from ``armora_gst_rules``.
    """

    _name = 'armora.gst.filing.validation'
    _description = 'Armora GST Filing Validation Service'

    @api.model
    def validate_filing(self, filing):
        filing.ensure_one()
        if filing.state in ('submitted', 'filed', 'cancelled'):
            filing._raise_readonly()

        filing.validation_result_ids.unlink()
        Result = self.env['armora.gst.validation.result']
        results = []

        # Per-line checks
        for line in filing.line_ids:
            line_issues = line._check_business_constraints()
            for severity, error_type, message in line_issues:
                results.append({
                    'filing_id': filing.id,
                    'line_id': line.id,
                    'move_id': line.move_id.id,
                    'partner_id': line.partner_id.id,
                    'severity': severity,
                    'error_type': error_type,
                    'message': message,
                    'hint': self._hint_for_error(error_type, line=line),
                })
            if any(i[0] == 'error' for i in line_issues):
                line.validation_state = 'error'
                line.validation_message = '\n'.join(i[2] for i in line_issues)
            elif any(i[0] == 'warning' for i in line_issues):
                line.validation_state = 'warning'
                line.validation_message = '\n'.join(i[2] for i in line_issues)
            else:
                line.validation_state = 'ok'
                line.validation_message = False

        # Duplicate invoice detection (same invoice number + date within filing)
        seen = {}
        for line in filing.line_ids:
            key = (line.invoice_number, line.invoice_date, line.move_id.id)
            if not line.invoice_number:
                continue
            # duplicates at move level once
            move_key = line.move_id.id or (line.invoice_number, line.invoice_date)
            if move_key in seen:
                continue
            # count moves with same number
            same = filing.line_ids.filtered(
                lambda l, num=line.invoice_number, mid=line.move_id.id: l.invoice_number == num and l.move_id.id != mid
            )
            if same:
                seen[move_key] = True
                results.append({
                    'filing_id': filing.id,
                    'line_id': line.id,
                    'move_id': line.move_id.id,
                    'partner_id': line.partner_id.id,
                    'severity': 'error',
                    'error_type': 'duplicate_invoice',
                    'message': 'Duplicate invoice number detected in filing snapshot: %s' % line.invoice_number,
                    'hint': self._hint_for_error('duplicate_invoice', line=line),
                })

        # Own company GSTIN structural check
        gstin_res = self.env['armora.gst.gstin.validator'].validate(filing.gstin, company=filing.company_id)
        if gstin_res['status'] == 'invalid':
            results.append({
                'filing_id': filing.id,
                'severity': 'error',
                'error_type': 'invalid_gstin',
                'message': 'Filing GSTIN: %s' % gstin_res['message'],
                'hint': self._hint_for_error('invalid_gstin'),
            })
        elif gstin_res['status'] == 'warning':
            results.append({
                'filing_id': filing.id,
                'severity': 'warning',
                'error_type': 'invalid_gstin',
                'message': 'Filing GSTIN: %s' % gstin_res['message'],
                'hint': self._hint_for_error('invalid_gstin'),
            })

        # Reconciliation vs accounting
        recon = self.env['armora.gst.filing.validation'].reconcile_filing(filing)
        tolerance = filing.company_id.armora_gst_recon_tolerance or 0.0
        currency = filing.currency_id
        prec = currency.decimal_places if currency else 2
        for field_name, label in [
            ('diff_taxable_value', 'Taxable Value'),
            ('diff_cgst', 'CGST'),
            ('diff_sgst', 'SGST'),
            ('diff_igst', 'IGST'),
            ('diff_cess', 'Cess'),
            ('diff_total_tax', 'Total Tax'),
            ('diff_invoice_value', 'Invoice Value'),
        ]:
            diff = abs(recon.get(field_name) or 0.0)
            if float_compare(diff, tolerance, precision_digits=prec) > 0:
                results.append({
                    'filing_id': filing.id,
                    'severity': 'error',
                    'error_type': 'reconciliation',
                    'message': '%s difference %.2f exceeds tolerance %.2f.' % (label, diff, tolerance),
                    'hint': self._hint_for_error('reconciliation'),
                })

        for miss in recon.get('missing_from_filing') or []:
            results.append({
                'filing_id': filing.id,
                'move_id': miss,
                'severity': 'error',
                'error_type': 'other',
                'message': 'Posted invoice is missing from filing snapshot (move id %s).' % miss,
                'hint': _(
                    'Open the invoice, confirm it belongs in this return period, then use '
                    'Regenerate Snapshot on the filing.'
                ),
            })
        for orphan in recon.get('orphan_lines') or []:
            results.append({
                'filing_id': filing.id,
                'line_id': orphan,
                'severity': 'warning',
                'error_type': 'other',
                'message': 'Filing line has no source invoice.',
                'hint': _(
                    'Prefer regenerating the snapshot from posted invoices instead of keeping '
                    'orphan snapshot lines.'
                ),
            })

        if results:
            Result.create(results)

        errors = len([r for r in results if r['severity'] == 'error'])
        warnings = len([r for r in results if r['severity'] == 'warning'])
        status = 'error' if errors else ('warning' if warnings else 'ok')
        filing.write({
            'validation_status': status,
            'validation_error_count': errors,
            'validation_warning_count': warnings,
            'state': 'validated' if filing.state in (
                'draft', 'data_loaded', 'validated', 'generated'
            ) else filing.state,
            'recon_taxable_value': recon.get('odoo_taxable_value'),
            'recon_cgst': recon.get('odoo_cgst'),
            'recon_sgst': recon.get('odoo_sgst'),
            'recon_igst': recon.get('odoo_igst'),
            'recon_cess': recon.get('odoo_cess'),
            'recon_total_tax': recon.get('odoo_total_tax'),
            'recon_invoice_value': recon.get('odoo_invoice_value'),
            'diff_taxable_value': recon.get('diff_taxable_value'),
            'diff_cgst': recon.get('diff_cgst'),
            'diff_sgst': recon.get('diff_sgst'),
            'diff_igst': recon.get('diff_igst'),
            'diff_cess': recon.get('diff_cess'),
            'diff_total_tax': recon.get('diff_total_tax'),
            'diff_invoice_value': recon.get('diff_invoice_value'),
        })
        return {
            'errors': errors,
            'warnings': warnings,
            'status': status,
        }

    @api.model
    def _hint_for_error(self, error_type, line=None):
        hints = {
            'missing_gstin': _(
                'Open the customer, set a valid GSTIN, then regenerate the filing snapshot.'
            ),
            'invalid_gstin': _(
                'Correct the company or partner GSTIN (15 characters, valid checksum), then regenerate.'
            ),
            'missing_hsn': _(
                'Set HSN/SAC on the product or invoice line, then regenerate the filing snapshot.'
            ),
            'missing_sac': _(
                'Set SAC on the service product or invoice line, then regenerate the filing snapshot.'
            ),
            'missing_place_of_supply': _(
                'Set Place of Supply on the invoice (Indian GST localization field), then regenerate.'
            ),
            'invalid_tax_rate': _(
                'Check GST tax configuration on the invoice lines and regenerate the snapshot.'
            ),
            'tax_mismatch': _(
                'Review tax amounts on the source invoice; fix taxes there, then regenerate.'
            ),
            'duplicate_invoice': _(
                'Resolve duplicate invoice numbers in Accounting, then regenerate the snapshot.'
            ),
            'missing_invoice_number': _(
                'Post or renumber the source invoice so it has a document number, then regenerate.'
            ),
            'invalid_invoice_date': _(
                'Move the invoice into the correct return period or adjust the filing period.'
            ),
            'missing_export_info': _(
                'Fill shipping bill number, date and port code on the export invoice, then regenerate.'
            ),
            'missing_cdn_reference': _(
                'Link the credit/debit note to the original invoice (number and date), then regenerate.'
            ),
            'cancelled_invoice': _(
                'Exclude cancelled documents or restore a valid posted invoice before filing.'
            ),
            'missing_tax_configuration': _(
                'Assign Indian GST taxes on the invoice lines, then regenerate the snapshot.'
            ),
            'reconciliation': _(
                'Compare snapshot totals with posted invoices. Fix source documents, then regenerate.'
            ),
            'negative_taxable': _(
                'Review negative taxable lines on the source invoice and regenerate.'
            ),
        }
        return hints.get(error_type, _(
            'Fix the source invoice or master data, then use Regenerate Snapshot on the filing.'
        ))

    @api.model
    def reconcile_filing(self, filing):
        """Compare snapshot totals with posted accounting documents in period."""
        filing.ensure_one()
        Extractor = self.env['armora.gst.data.extractor']
        moves = self.env['account.move'].search(Extractor._period_domain(filing))
        snap_moves = filing.line_ids.mapped('move_id')

        # Snapshot aggregates (unique invoice value once per move)
        taxable = sum(filing.line_ids.mapped('taxable_value'))
        cgst = sum(filing.line_ids.mapped('cgst_amount'))
        sgst = sum(filing.line_ids.mapped('sgst_amount'))
        igst = sum(filing.line_ids.mapped('igst_amount'))
        cess = sum(filing.line_ids.mapped('cess_amount'))
        total_tax = sum(filing.line_ids.mapped('total_tax'))
        invoice_value = sum(abs(m.amount_total_signed) for m in snap_moves)

        odoo_taxable = 0.0
        odoo_cgst = odoo_sgst = odoo_igst = odoo_cess = 0.0
        for move in moves:
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type in (False, 'product') and not l.tax_line_id
            ):
                tax_info = Extractor._tax_amounts_for_line(move, line)
                odoo_taxable += tax_info['taxable_value']
                odoo_cgst += tax_info['cgst_amount']
                odoo_sgst += tax_info['sgst_amount']
                odoo_igst += tax_info['igst_amount']
                odoo_cess += tax_info['cess_amount']
        odoo_total_tax = odoo_cgst + odoo_sgst + odoo_igst + odoo_cess
        odoo_invoice_value = sum(abs(m.amount_total_signed) for m in moves)

        missing = (moves - snap_moves).ids
        orphans = filing.line_ids.filtered(lambda l: not l.move_id).ids

        currency = filing.currency_id
        money = Extractor._money
        return {
            'odoo_taxable_value': money(odoo_taxable, currency),
            'odoo_cgst': money(odoo_cgst, currency),
            'odoo_sgst': money(odoo_sgst, currency),
            'odoo_igst': money(odoo_igst, currency),
            'odoo_cess': money(odoo_cess, currency),
            'odoo_total_tax': money(odoo_total_tax, currency),
            'odoo_invoice_value': money(odoo_invoice_value, currency),
            'diff_taxable_value': money(taxable - odoo_taxable, currency),
            'diff_cgst': money(cgst - odoo_cgst, currency),
            'diff_sgst': money(sgst - odoo_sgst, currency),
            'diff_igst': money(igst - odoo_igst, currency),
            'diff_cess': money(cess - odoo_cess, currency),
            'diff_total_tax': money(total_tax - odoo_total_tax, currency),
            'diff_invoice_value': money(invoice_value - odoo_invoice_value, currency),
            'missing_from_filing': missing,
            'orphan_lines': orphans,
        }
