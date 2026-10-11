# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools.float_utils import float_compare, float_round


class RnGstClassification(models.AbstractModel):
    """Deterministic GSTR-1 supply classification from Odoo l10n_in fields."""

    _name = 'rn.gst.classification'
    _description = 'Armora GST Classification'

    @api.model
    def _money(self, amount, currency):
        return self.env['rn.gst.money'].round_amount(amount, currency=currency)

    @api.model
    def _tax_split(self, move_line):
        """Return rate and CGST/SGST/IGST/CESS amounts for one invoice line."""
        currency = move_line.currency_id or move_line.company_currency_id or move_line.company_id.currency_id
        taxable = abs(move_line.balance) if move_line.move_id.move_type in ('out_refund', 'in_refund') else abs(move_line.balance)
        # Prefer price_subtotal for customer invoices in company currency
        if move_line.currency_id and move_line.currency_id == move_line.company_id.currency_id:
            taxable = abs(move_line.price_subtotal)
        elif move_line.price_subtotal and not move_line.currency_id:
            taxable = abs(move_line.price_subtotal)

        cgst = sgst = igst = cess = 0.0
        rate = 0.0
        is_rc = False
        for tax in move_line.tax_ids.flatten_taxes_hierarchy():
            tax_type = getattr(tax, 'l10n_in_gst_tax_type', False)
            if getattr(tax, 'l10n_in_reverse_charge', False):
                is_rc = True
            amount = abs(tax.amount or 0.0)
            # Approximate tax amount from rate on taxable base (exact from tax details preferred)
            tax_amount = self._money(taxable * amount / 100.0, currency)
            if tax_type == 'cgst':
                cgst += tax_amount
                rate += amount
            elif tax_type == 'sgst':
                sgst += tax_amount
                rate += amount
            elif tax_type == 'igst':
                igst += tax_amount
                rate += amount
            elif tax_type == 'cess':
                cess += tax_amount
            elif not tax_type and tax.amount_type == 'percent':
                # Untagged percent tax: treat as IGST-like if only one, else split later
                igst += tax_amount
                rate += amount

        # Prefer computed tax totals from move line when available
        if move_line.price_total and move_line.price_subtotal is not None:
            line_tax = abs(move_line.price_total) - abs(move_line.price_subtotal)
            computed = cgst + sgst + igst + cess
            if float_compare(computed, 0.0, precision_digits=currency.decimal_places) == 0 and line_tax:
                # fallback keep igst bucket
                igst = self._money(line_tax, currency)

        return {
            'taxable_value': self._money(taxable, currency),
            'gst_rate': float_round(rate, precision_digits=2),
            'cgst_amount': self._money(cgst, currency),
            'sgst_amount': self._money(sgst, currency),
            'igst_amount': self._money(igst, currency),
            'cess_amount': self._money(cess, currency),
            'is_reverse_charge': is_rc,
            'currency': currency,
        }

    @api.model
    def classify_move_line(self, move, move_line, company=None):
        """Classify one invoice line into GSTR-1 section / supply type."""
        company = company or move.company_id
        errors = []
        currency = company.currency_id
        tax_info = self._tax_split(move_line)

        treatment = move.l10n_in_gst_treatment or move.partner_id.l10n_in_gst_treatment or 'consumer'
        pos_state = move.l10n_in_state_id
        company_state = company.state_id
        pos_code = pos_state.l10n_in_tin if pos_state else False
        partner_gstin = move.l10n_in_gstin or move.partner_id.vat or ''

        is_credit = move.move_type == 'out_refund'
        is_debit = bool(getattr(move, 'debit_origin_id', False)) and move.move_type == 'out_invoice'
        document_type = 'credit_note' if is_credit else ('debit_note' if is_debit else 'invoice')

        is_export = treatment in ('overseas',) or (pos_code == '96')
        is_sez = treatment == 'special_economic_zone'
        is_deemed = treatment == 'deemed_export'
        is_nil = False
        is_exempt = False
        is_non_gst = False

        # Detect nil/exempt/non-gst via tax tags when present
        for tax in move_line.tax_ids.flatten_taxes_hierarchy():
            tag_names = ' '.join(tax.invoice_repartition_line_ids.tag_ids.mapped('name')).lower()
            in_tax_type = getattr(tax, 'l10n_in_tax_type', False)
            if 'nil' in tag_names or 'zero' in tag_names or in_tax_type == 'nil_rated':
                is_nil = True
            if 'exempt' in tag_names or in_tax_type == 'exempt':
                is_exempt = True
            if ('non' in tag_names and 'gst' in tag_names) or in_tax_type == 'non_gst':
                is_non_gst = True
            if not move_line.tax_ids:
                # no tax: may be nil/exempt/non-gst; leave for validation if unknown
                pass

        if not pos_state and not is_export:
            errors.append('Place of supply is missing on the invoice.')

        interstate = False
        if pos_state and company_state:
            interstate = pos_state.id != company_state.id
        if pos_code == '96':
            interstate = True

        tax_type = 'igst' if (interstate or is_export or is_sez) else 'cgst_sgst'
        if tax_info['igst_amount'] and not (tax_info['cgst_amount'] or tax_info['sgst_amount']):
            tax_type = 'igst'
        elif tax_info['cgst_amount'] or tax_info['sgst_amount']:
            tax_type = 'cgst_sgst'

        export_type = False
        if is_export or is_sez:
            # With payment / without payment: LUT fiscal position often zero IGST
            if float_compare(tax_info['igst_amount'] + tax_info['cgst_amount'] + tax_info['sgst_amount'], 0.0,
                             precision_digits=currency.decimal_places) == 0:
                export_type = 'wopay'
            else:
                export_type = 'wpay'
            if not move.l10n_in_shipping_bill_number and is_export:
                errors.append('Export shipping bill number is missing.')
            if not move.l10n_in_shipping_bill_date and is_export:
                errors.append('Export shipping bill date is missing.')
            if not move.l10n_in_shipping_port_code_id and is_export:
                errors.append('Export port code is missing.')

        # Registered B2B-like treatments
        registered = treatment in (
            'regular', 'composition', 'special_economic_zone', 'deemed_export', 'uin_holders'
        ) and bool(partner_gstin)

        gst_table = False
        supply_type = False

        if is_credit or is_debit:
            if registered or partner_gstin:
                gst_table = 'cdnr'
                supply_type = 'cdnr'
            else:
                gst_table = 'cdnur'
                supply_type = 'cdnur'
            if not move.reversed_entry_id and is_credit:
                errors.append('Credit note is missing the original invoice reference (reversed entry).')
        elif is_non_gst:
            gst_table = 'nil'
            supply_type = 'non_gst'
        elif is_exempt:
            gst_table = 'nil'
            supply_type = 'exempt'
        elif is_nil or (
            float_compare(tax_info['gst_rate'], 0.0, precision_digits=2) == 0
            and not is_export and not is_sez and not registered
        ):
            gst_table = 'nil'
            supply_type = 'nil_rated'
        elif is_export:
            gst_table = 'exp'
            supply_type = 'export'
        elif is_sez:
            gst_table = 'b2b'
            supply_type = 'export'  # reported with SEZ treatment; table still B2B-like in many portals
        elif is_deemed:
            gst_table = 'b2b'
            supply_type = 'deemed_export'
        elif registered or partner_gstin:
            gst_table = 'b2b'
            supply_type = 'b2b'
            if not partner_gstin:
                errors.append('Customer GSTIN is missing for B2B supply.')
        else:
            # B2C
            threshold = company.rn_gst_b2cl_threshold or 250000.0
            invoice_value = abs(move.amount_total_signed)
            if interstate and float_compare(invoice_value, threshold, precision_digits=currency.decimal_places) > 0:
                gst_table = 'b2cl'
                supply_type = 'b2cl'
            else:
                gst_table = 'b2cs'
                supply_type = 'b2cs'

        hsn = move_line.l10n_in_hsn_code or move_line.product_id.l10n_in_hsn_code or ''
        if not hsn and gst_table not in ('nil',):
            errors.append('HSN/SAC code is missing on invoice line / product.')

        return {
            'gst_table': gst_table,
            'supply_type': supply_type,
            'tax_type': tax_type,
            'document_type': document_type,
            'place_of_supply': pos_state.display_name if pos_state else False,
            'place_of_supply_code': pos_code,
            'is_reverse_charge': tax_info['is_reverse_charge'] or False,
            'is_export': bool(is_export or is_sez),
            'export_type': export_type,
            'hsn_code': hsn,
            'sac_code': False,
            'gst_rate': tax_info['gst_rate'],
            'taxable_value': tax_info['taxable_value'],
            'cgst_amount': tax_info['cgst_amount'],
            'sgst_amount': tax_info['sgst_amount'],
            'igst_amount': tax_info['igst_amount'],
            'cess_amount': tax_info['cess_amount'],
            'total_tax': self._money(
                tax_info['cgst_amount'] + tax_info['sgst_amount'] + tax_info['igst_amount'] + tax_info['cess_amount'],
                currency,
            ),
            'errors': errors,
            'treatment': treatment,
            'partner_gstin': partner_gstin,
        }
