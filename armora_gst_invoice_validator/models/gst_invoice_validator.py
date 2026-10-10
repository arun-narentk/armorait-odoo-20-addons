# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models


class ArmoraGstInvoiceValidator(models.AbstractModel):
    """Pre-post GST validation engine for Indian invoices and bills."""

    _name = 'armora.gst.invoice.validator'
    _description = 'Armora GST Invoice Validator'

    HSN_RE = re.compile(r'^\d{4}$|^\d{6}$|^\d{8}$')
    INVOICE_NAME_RE = re.compile(r'^[a-zA-Z0-9\-\/]+$')

    @api.model
    def _product_lines(self, move):
        return move.invoice_line_ids.filtered(
            lambda l: l.display_type in (False, 'product') and not l.tax_line_id
        )

    @api.model
    def _issue(self, severity, error_type, message, hint=None, move_line=None):
        return {
            'severity': severity,
            'error_type': error_type,
            'message': message,
            'hint': hint or False,
            'move_line_id': move_line.id if move_line else False,
        }

    @api.model
    def _score_from_issues(self, issues):
        score = 100
        for issue in issues:
            if issue['severity'] == 'error':
                score -= 12
            elif issue['severity'] == 'warning':
                score -= 5
            elif issue['severity'] == 'review':
                score -= 2
        return max(0, min(100, score))

    @api.model
    def validate_move(self, move, persist=True):
        """Run checks and optionally store issue rows on the move."""
        move.ensure_one()
        issues = []
        if move.country_code != 'IN' or not move.is_invoice(include_receipts=True):
            if persist:
                move.armora_gst_issue_ids.unlink()
                move.write({
                    'armora_gst_validation_status': 'skipped',
                    'armora_gst_validation_score': 100,
                    'armora_gst_validated_at': fields.Datetime.now(),
                })
            return {'issues': [], 'score': 100, 'status': 'skipped'}

        company = move.company_id
        if move.is_sale_document(include_receipts=True) and not company.armora_gst_validate_sales:
            status = 'skipped'
            if persist:
                move.armora_gst_issue_ids.unlink()
                move.write({
                    'armora_gst_validation_status': status,
                    'armora_gst_validation_score': 100,
                    'armora_gst_validated_at': fields.Datetime.now(),
                })
            return {'issues': [], 'score': 100, 'status': status}
        if move.is_purchase_document(include_receipts=True) and not company.armora_gst_validate_purchases:
            status = 'skipped'
            if persist:
                move.armora_gst_issue_ids.unlink()
                move.write({
                    'armora_gst_validation_status': status,
                    'armora_gst_validation_score': 100,
                    'armora_gst_validated_at': fields.Datetime.now(),
                })
            return {'issues': [], 'score': 100, 'status': status}

        issues.extend(self._check_company(move))
        issues.extend(self._check_partner_gstin(move))
        issues.extend(self._check_place_of_supply(move))
        issues.extend(self._check_pos_vs_gstin(move))
        issues.extend(self._check_invoice_series(move))
        issues.extend(self._check_lines(move))
        issues.extend(self._check_export(move))
        issues.extend(self._check_credit_note(move))
        issues.extend(self._check_einvoice_eligibility(move))

        score = self._score_from_issues(issues)
        if any(i['severity'] == 'error' for i in issues):
            status = 'error'
        elif any(i['severity'] == 'warning' for i in issues):
            status = 'warning'
        else:
            status = 'ok'

        if persist:
            move.armora_gst_issue_ids.unlink()
            if issues:
                self.env['armora.gst.invoice.issue'].create([{
                    'move_id': move.id,
                    'move_line_id': i['move_line_id'],
                    'severity': i['severity'],
                    'error_type': i['error_type'],
                    'message': i['message'],
                    'hint': i['hint'],
                } for i in issues])
            move.write({
                'armora_gst_validation_status': status,
                'armora_gst_validation_score': score,
                'armora_gst_validated_at': fields.Datetime.now(),
            })
        return {'issues': issues, 'score': score, 'status': status}

    @api.model
    def _check_company(self, move):
        issues = []
        company = move.company_id
        if not company.vat:
            issues.append(self._issue(
                'error', 'missing_gstin',
                _('Company GSTIN is missing on %s.') % company.name,
                _('Set the company VAT/GSTIN under Settings → Companies.'),
            ))
        else:
            res = self.env['armora.gst.gstin.validator'].validate(company.vat, company=company)
            if res['status'] == 'invalid':
                issues.append(self._issue(
                    'error', 'invalid_gstin',
                    _('Company GSTIN is invalid: %s') % res['message'],
                    _('Correct the company GSTIN. It must be 15 characters with a valid checksum.'),
                ))
            elif res['status'] == 'warning':
                issues.append(self._issue('warning', 'invalid_gstin', res['message']))
        if not company.state_id:
            issues.append(self._issue(
                'error', 'other',
                _('Company state is missing. Place of supply and tax type cannot be determined reliably.'),
                _('Set the State on the company address.'),
            ))
        return issues

    @api.model
    def _check_partner_gstin(self, move):
        issues = []
        treatment = move.l10n_in_gst_treatment or 'consumer'
        gstin = move.l10n_in_gstin or move.partner_id.vat or ''
        needs_gstin = treatment in (
            'regular', 'composition', 'special_economic_zone', 'deemed_export', 'uin_holders'
        )
        if needs_gstin and not gstin:
            issues.append(self._issue(
                'error', 'missing_gstin',
                _('Partner "%s" requires a GSTIN for GST treatment "%s".') % (
                    move.partner_id.display_name, treatment,
                ),
                _('Add the partner GSTIN (VAT) or change the GST treatment if they are unregistered/consumer.'),
            ))
        elif gstin:
            res = self.env['armora.gst.gstin.validator'].validate(gstin, company=move.company_id)
            if res['status'] == 'invalid':
                issues.append(self._issue(
                    'error', 'invalid_gstin',
                    _('Partner GSTIN "%s" is invalid: %s') % (gstin, res['message']),
                    _('Ask the partner for the correct 15-character GSTIN, or correct a typing error.'),
                ))
            elif res['status'] == 'warning':
                issues.append(self._issue('warning', 'invalid_gstin', res['message']))
        return issues

    @api.model
    def _check_place_of_supply(self, move):
        issues = []
        if move.is_sale_document(include_receipts=True) and not move.l10n_in_state_id:
            if move.l10n_in_gst_treatment != 'overseas':
                issues.append(self._issue(
                    'error', 'missing_place_of_supply',
                    _('Place of supply is missing on this invoice.'),
                    _('Set Place of Supply (l10n_in_state_id). It usually follows the customer/shipping state.'),
                ))
        elif move.l10n_in_state_id and not move.l10n_in_state_id.l10n_in_tin:
            issues.append(self._issue(
                'error', 'missing_place_of_supply',
                _('Place of supply "%s" has no GST state code (TIN).') % move.l10n_in_state_id.display_name,
                _('Use an Indian state with a valid GST TIN, or Other Country (96) for exports.'),
            ))
        return issues

    @api.model
    def _check_pos_vs_gstin(self, move):
        """Detect GSTIN state vs place of supply mismatches for registered parties."""
        issues = []
        gstin = (move.l10n_in_gstin or move.partner_id.vat or '').strip().upper()
        pos = move.l10n_in_state_id
        if not gstin or len(gstin) < 2 or not pos or not pos.l10n_in_tin:
            return issues
        if move.l10n_in_gst_treatment in ('overseas', 'consumer', 'unregistered'):
            return issues
        gstin_state = gstin[:2]
        pos_tin = pos.l10n_in_tin
        if pos_tin in ('96', '97'):
            return issues
        if gstin_state != pos_tin:
            gstin_state_name = self.env['res.country.state'].search([
                ('country_id.code', '=', 'IN'),
                ('l10n_in_tin', '=', gstin_state),
            ], limit=1).display_name or gstin_state
            severity = 'error' if move.company_id.armora_gst_strict_pos_gstin else 'warning'
            issues.append(self._issue(
                severity, 'pos_gstin_mismatch',
                _(
                    'Customer GSTIN belongs to %(gstin_state)s (code %(gstin_code)s) '
                    'but place of supply is %(pos)s (code %(pos_code)s).'
                ) % {
                    'gstin_state': gstin_state_name,
                    'gstin_code': gstin_state,
                    'pos': pos.display_name,
                    'pos_code': pos_tin,
                },
                _(
                    'For most B2B invoices, place of supply matches the customer GSTIN state. '
                    'If bill-to and ship-to states differ on purpose, disable "Strict Place of Supply '
                    'vs GSTIN State" in Armora GST settings, or use Force Post.'
                ),
            ))
        return issues

    @api.model
    def _check_invoice_series(self, move):
        issues = []
        if not move.is_sale_document(include_receipts=True):
            return issues
        name = move.name or ''
        if not name or name == '/':
            # Draft sequences may still be '/'
            return issues
        if len(name) > 16:
            issues.append(self._issue(
                'error', 'invoice_series',
                _('Invoice number "%s" exceeds 16 characters (GST Rule 46(b)).') % name,
                _('Shorten the journal sequence so posted invoice numbers stay within 16 characters.'),
            ))
        if not self.INVOICE_NAME_RE.match(name):
            issues.append(self._issue(
                'error', 'invoice_series',
                _('Invoice number "%s" contains characters not allowed under GST Rule 46(b).') % name,
                _('Only letters, digits, hyphen (-) and slash (/) are allowed.'),
            ))
        return issues

    @api.model
    def _check_lines(self, move):
        issues = []
        company = move.company_id
        company_state = company.state_id
        pos = move.l10n_in_state_id
        interstate = bool(pos and company_state and pos.id != company_state.id)
        if pos and pos.l10n_in_tin == '96':
            interstate = True
        min_hsn = int(company.l10n_in_hsn_code_digit or 0) if company.l10n_in_hsn_code_digit else 0

        for line in self._product_lines(move):
            hsn = line.l10n_in_hsn_code or line.product_id.l10n_in_hsn_code or ''
            if not hsn:
                issues.append(self._issue(
                    'error', 'missing_hsn',
                    _('HSN/SAC is missing on line "%s".') % (line.name or line.product_id.display_name),
                    _('Set HSN/SAC on the product or invoice line.'),
                    move_line=line,
                ))
            elif not self.HSN_RE.match(hsn) or (min_hsn and len(hsn) < min_hsn):
                issues.append(self._issue(
                    'error', 'missing_hsn',
                    _('HSN/SAC "%s" on line "%s" is invalid for company HSN digit rules.') % (
                        hsn, line.name or line.product_id.display_name,
                    ),
                    _('Use a 4/6/8 digit HSN/SAC meeting the company configuration.'),
                    move_line=line,
                ))

            taxes = line.tax_ids.flatten_taxes_hierarchy()
            if not taxes:
                issues.append(self._issue(
                    'warning', 'missing_tax_configuration',
                    _('No tax configured on line "%s". Confirm nil-rated / exempt / non-GST intent.') % (
                        line.name or line.product_id.display_name
                    ),
                    _('Add the correct GST taxes, or keep empty only for intentional nil/exempt/non-GST lines.'),
                    move_line=line,
                ))
                continue

            types = {t.l10n_in_gst_tax_type for t in taxes if t.l10n_in_gst_tax_type}
            has_igst = 'igst' in types
            has_cgst = 'cgst' in types
            has_sgst = 'sgst' in types
            if interstate or move.l10n_in_gst_treatment in ('overseas', 'special_economic_zone'):
                if (has_cgst or has_sgst) and not has_igst:
                    issues.append(self._issue(
                        'error', 'tax_type_mismatch',
                        _('Interstate/export line "%s" uses CGST/SGST instead of IGST.') % (
                            line.name or line.product_id.display_name
                        ),
                        _('Use an IGST fiscal position / tax mapping for interstate or export supplies.'),
                        move_line=line,
                    ))
            else:
                if has_igst and not (has_cgst or has_sgst):
                    issues.append(self._issue(
                        'error', 'tax_type_mismatch',
                        _('Intrastate line "%s" uses IGST instead of CGST/SGST.') % (
                            line.name or line.product_id.display_name
                        ),
                        _('Use CGST+SGST taxes for supplies within the company state.'),
                        move_line=line,
                    ))
                if has_cgst ^ has_sgst:
                    issues.append(self._issue(
                        'warning', 'tax_type_mismatch',
                        _('Line "%s" has only one of CGST/SGST. Both are normally required together.') % (
                            line.name or line.product_id.display_name
                        ),
                        _('Check the tax group mapping so CGST and SGST are applied together.'),
                        move_line=line,
                    ))

            # Soft RCM signal on sales is unusual
            if move.is_sale_document(include_receipts=True) and any(
                getattr(t, 'l10n_in_reverse_charge', False) for t in taxes
            ):
                issues.append(self._issue(
                    'review', 'rcm_mismatch',
                    _('Reverse charge tax found on customer invoice line "%s".') % (
                        line.name or line.product_id.display_name
                    ),
                    _('Confirm whether this supply is truly under reverse charge.'),
                    move_line=line,
                ))
        return issues

    @api.model
    def _check_export(self, move):
        issues = []
        if move.l10n_in_gst_treatment != 'overseas' and not (
            move.l10n_in_state_id and move.l10n_in_state_id.l10n_in_tin == '96'
        ):
            return issues
        if not move.is_sale_document(include_receipts=True):
            return issues
        if not move.l10n_in_shipping_bill_number:
            issues.append(self._issue(
                'warning', 'missing_export_info',
                _('Export invoice is missing shipping bill number.'),
                _('Enter shipping bill details when available for GSTR-1 export reporting.'),
            ))
        if not move.l10n_in_shipping_bill_date:
            issues.append(self._issue(
                'warning', 'missing_export_info',
                _('Export invoice is missing shipping bill date.'),
            ))
        if not move.l10n_in_shipping_port_code_id:
            issues.append(self._issue(
                'warning', 'missing_export_info',
                _('Export invoice is missing port code.'),
            ))
        return issues

    @api.model
    def _check_credit_note(self, move):
        issues = []
        if move.move_type not in ('out_refund', 'in_refund'):
            return issues
        if not move.reversed_entry_id:
            issues.append(self._issue(
                'error', 'missing_cdn_reference',
                _('Credit/debit note has no original invoice reference (reversed entry).'),
                _('Create the credit note from the original invoice so GST CDNR/CDNUR reporting stays auditable.'),
            ))
        return issues

    @api.model
    def _check_einvoice_eligibility(self, move):
        """Informational only: do not invent IRN integration."""
        issues = []
        if not move.is_sale_document(include_receipts=True):
            return issues
        # If EDI module fields exist, surface pending state as review/info
        if 'l10n_in_edi_status' in move._fields:
            # Presence of EDI fields means e-Invoice stack may be installed
            treatment = move.l10n_in_gst_treatment
            if treatment in ('regular', 'special_economic_zone', 'deemed_export') and move.partner_id.vat:
                issues.append(self._issue(
                    'info', 'einvoice_eligibility',
                    _('This B2B invoice may be e-Invoice eligible. Confirm IRN generation after posting.'),
                    _('Use Odoo Indian e-Invoicing after posting; Armora only monitors eligibility here.'),
                ))
        return issues

    @api.model
    def blocking_errors(self, move):
        result = self.validate_move(move, persist=True)
        return [i for i in result['issues'] if i['severity'] == 'error']
