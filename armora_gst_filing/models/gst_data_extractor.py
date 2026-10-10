# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.tools.float_utils import float_round


class ArmoraGstDataExtractor(models.AbstractModel):
    """Extract posted customer documents into GST filing snapshot lines."""

    _name = 'armora.gst.data.extractor'
    _description = 'Armora GST Data Extractor'

    @api.model
    def _money(self, amount, currency):
        return self.env['armora.gst.money'].round_amount(amount, currency=currency)

    @api.model
    def _period_domain(self, filing):
        return [
            ('company_id', '=', filing.company_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('invoice_date', '>=', filing.period_start),
            ('invoice_date', '<=', filing.period_end),
            ('country_code', '=', 'IN'),
        ]

    @api.model
    def _rate_once(self, tax, rated_tax_ids):
        if tax.id in rated_tax_ids:
            return 0.0
        rated_tax_ids.add(tax.id)
        return abs(tax.amount or 0.0)

    @api.model
    def _tax_amounts_for_line(self, move, move_line):
        """Compute taxable + GST split using Odoo tax compute_all (Decimal-rounded)."""
        company = move.company_id
        currency = move.currency_id or company.currency_id
        is_refund = move.move_type in ('out_refund', 'in_refund')
        taxes = move_line.tax_ids.flatten_taxes_hierarchy()
        price_unit = move_line.price_unit
        if move_line.discount:
            price_unit = price_unit * (1 - (move_line.discount or 0.0) / 100.0)

        if not taxes:
            taxable = abs(move_line.price_subtotal)
            if move.currency_id and move.currency_id != company.currency_id:
                taxable = abs(move_line.balance)
            return {
                'taxable_value': self._money(taxable, company.currency_id),
                'gst_rate': 0.0,
                'cgst_amount': 0.0,
                'sgst_amount': 0.0,
                'igst_amount': 0.0,
                'cess_amount': 0.0,
                'is_reverse_charge': False,
            }

        res = taxes.compute_all(
            price_unit,
            currency=move.currency_id or company.currency_id,
            quantity=move_line.quantity,
            product=move_line.product_id,
            partner=move.partner_id,
            is_refund=is_refund,
            handle_price_include=True,
        )
        taxable = abs(res.get('total_excluded', 0.0))
        # Convert to company currency when needed
        if move.currency_id and move.currency_id != company.currency_id and move_line.balance:
            # Prefer accounting balance for company currency taxable base
            taxable = abs(move_line.balance)

        cgst = sgst = igst = cess = 0.0
        rate = 0.0
        is_rc = False
        tax_map = {t.id: t for t in taxes}
        # compute_all returns tax in invoice currency. Convert to company currency:
        # invoice_currency_rate is company currency units per 1 invoice currency unit,
        # so company_amount = invoice_amount / rate (never invert when rate < 1).
        foreign_currency = bool(
            move.currency_id
            and company.currency_id
            and move.currency_id != company.currency_id
        )
        rate_val = move.invoice_currency_rate or 1.0
        # Export, SEZ and reverse charge taxes carry a +100% and a -100% tax
        # repartition line (net zero on the invoice). Report the tax once by
        # skipping the offsetting line, and count each tax rate only once.
        offset_rep_line_ids = set(
            taxes.invoice_repartition_line_ids.filtered(lambda r: r.factor_percent < 0).ids
            + taxes.refund_repartition_line_ids.filtered(lambda r: r.factor_percent < 0).ids
        )
        rated_tax_ids = set()
        for tax_line in res.get('taxes', []):
            if tax_line.get('tax_repartition_line_id') in offset_rep_line_ids:
                continue
            tax = tax_map.get(tax_line.get('id'))
            amount = abs(tax_line.get('amount') or 0.0)
            if foreign_currency and rate_val:
                amount = amount / rate_val
            tax_type = getattr(tax, 'l10n_in_gst_tax_type', False) if tax else False
            if tax and getattr(tax, 'l10n_in_reverse_charge', False):
                is_rc = True
            tax_amount_company = self._money(amount, company.currency_id)
            if tax_type == 'cgst':
                cgst += tax_amount_company
                rate += self._rate_once(tax, rated_tax_ids)
            elif tax_type == 'sgst':
                sgst += tax_amount_company
                rate += self._rate_once(tax, rated_tax_ids)
            elif tax_type == 'igst':
                igst += tax_amount_company
                rate += self._rate_once(tax, rated_tax_ids)
            elif tax_type == 'cess':
                cess += tax_amount_company
            elif tax and tax.amount_type == 'percent':
                # Untagged: put under IGST bucket for interstate/export heuristics later
                igst += tax_amount_company
                rate += self._rate_once(tax, rated_tax_ids)

        return {
            'taxable_value': self._money(taxable, company.currency_id),
            'gst_rate': float_round(rate, precision_digits=2),
            'cgst_amount': self._money(cgst, company.currency_id),
            'sgst_amount': self._money(sgst, company.currency_id),
            'igst_amount': self._money(igst, company.currency_id),
            'cess_amount': self._money(cess, company.currency_id),
            'is_reverse_charge': is_rc,
        }

    @api.model
    def extract_to_filing(self, filing, regenerate=False):
        """Create snapshot lines for a filing. Never touches source invoices.

        After a successful load the filing moves to ``data_loaded`` and snapshot
        lines become immutable until an explicit regenerate or reset to draft.
        """
        filing.ensure_one()
        if filing.state in ('submitted', 'filed', 'cancelled'):
            filing._raise_readonly(message='Cannot load or regenerate snapshot on submitted/filed/cancelled filings.')
        if filing.state == 'generated' and not regenerate:
            filing._raise_readonly(
                message=_(
                    'Filing already has a generated GSTN Offline Tool Excel. '
                    'Reset to draft or use Regenerate Snapshot.'
                )
            )

        reloadable_states = ('draft', 'data_loaded', 'validated', 'generated')
        if filing.line_ids:
            if not regenerate and filing.state not in ('draft',):
                return filing
            if regenerate or filing.state == 'draft':
                if filing.state not in reloadable_states:
                    filing._raise_readonly()
                filing.line_ids.with_context(armora_gst_regenerate_snapshot=True).unlink()
                filing.validation_result_ids.unlink()

        Classification = self.env['armora.gst.classification']
        moves = self.env['account.move'].search(self._period_domain(filing), order='invoice_date, name')
        line_vals = []
        for move in moves:
            invoice_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type in (False, 'product') and not l.tax_line_id
            )
            for move_line in invoice_lines:
                classified = Classification.classify_move_line(move, move_line, company=filing.company_id)
                tax_info = self._tax_amounts_for_line(move, move_line)
                # Prefer extractor monetary amounts; keep classification rates/types
                total_tax = self._money(
                    tax_info['cgst_amount'] + tax_info['sgst_amount'] + tax_info['igst_amount'] + tax_info['cess_amount'],
                    filing.company_id.currency_id,
                )
                origin = move.reversed_entry_id
                if not origin and getattr(move, 'debit_origin_id', False):
                    origin = move.debit_origin_id
                hsn = move_line.l10n_in_hsn_code or move_line.product_id.l10n_in_hsn_code or ''
                port = move.l10n_in_shipping_port_code_id.code if move.l10n_in_shipping_port_code_id else False
                invoice_value = abs(move.amount_total_signed)
                vals = {
                    'filing_id': filing.id,
                    'move_id': move.id,
                    'move_line_id': move_line.id,
                    'partner_id': move.partner_id.id,
                    'partner_gstin': classified.get('partner_gstin') or move.l10n_in_gstin or move.partner_id.vat or '',
                    'partner_name': move.partner_id.display_name,
                    'invoice_date': move.invoice_date,
                    'invoice_number': move.name,
                    'document_type': classified['document_type'],
                    'document_date': move.invoice_date,
                    'original_invoice_number': origin.name if origin else False,
                    'original_invoice_date': origin.invoice_date if origin else False,
                    'place_of_supply': classified.get('place_of_supply'),
                    'place_of_supply_code': classified.get('place_of_supply_code'),
                    'supply_type': classified.get('supply_type'),
                    'is_reverse_charge': tax_info['is_reverse_charge'] or classified.get('is_reverse_charge'),
                    'is_export': classified.get('is_export'),
                    'export_type': classified.get('export_type'),
                    'port_code': port,
                    'shipping_bill_number': move.l10n_in_shipping_bill_number,
                    'shipping_bill_date': move.l10n_in_shipping_bill_date,
                    'hsn_code': hsn,
                    'description': move_line.name,
                    'quantity': move_line.quantity,
                    'uom': move_line.product_uom_id.name if move_line.product_uom_id else False,
                    'taxable_value': tax_info['taxable_value'],
                    'gst_rate': tax_info['gst_rate'] or classified.get('gst_rate'),
                    'cgst_amount': tax_info['cgst_amount'],
                    'sgst_amount': tax_info['sgst_amount'],
                    'igst_amount': tax_info['igst_amount'],
                    'cess_amount': tax_info['cess_amount'],
                    'total_tax': total_tax,
                    'invoice_value': self._money(invoice_value, filing.company_id.currency_id),
                    'gst_section': classified.get('gst_table'),
                    'gst_table': classified.get('gst_table'),
                    'validation_state': 'error' if classified.get('errors') else 'ok',
                    'validation_message': '\n'.join(classified.get('errors') or []) or False,
                }
                line_vals.append(vals)

        # Create while filing is still draft so line create guards allow insert,
        # then move to data_loaded (snapshot locked).
        if line_vals:
            self.env['armora.gst.filing.line'].with_context(
                armora_gst_regenerate_snapshot=True,
            ).create(line_vals)

        filing.write({
            'state': 'data_loaded',
            'validation_status': 'pending',
            'validation_error_count': 0,
            'validation_warning_count': 0,
            'generated_file': False,
            'generated_filename': False,
            'generated_at': False,
            'generated_by': False,
            'template_version': False,
        })
        filing._compute_summary_from_lines()
        return filing
