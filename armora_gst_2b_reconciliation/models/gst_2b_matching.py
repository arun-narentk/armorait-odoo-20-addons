# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare


class ArmoraGst2bMatching(models.AbstractModel):
    """Match GSTR-2B lines to posted vendor bills."""

    _name = 'armora.gst.2b.matching'
    _description = 'Armora GSTR-2B Matching Engine'

    @api.model
    def match_reconciliation(self, reconciliation):
        reconciliation.ensure_one()
        # Drop previous Odoo-only gap lines; rebuild from current bills
        reconciliation.line_ids.filtered(lambda l: l.source == 'odoo').unlink()

        bills = self._period_vendor_bills(reconciliation)
        # GSTR-2B also carries supplier invoices dated before the period (filed
        # late by the supplier), so match against those bills too. Only period
        # bills are reported as missing in 2B below.
        bill_map = self._index_bills(bills | self._earlier_vendor_bills(reconciliation))
        used_bill_ids = set()

        company = reconciliation.company_id
        amount_tol = company.armora_gst_2b_amount_tolerance or 0.0
        date_tol = company.armora_gst_2b_date_tolerance_days or 0
        currency = reconciliation.currency_id
        prec = currency.decimal_places if currency else 2

        for line in reconciliation.line_ids.filtered(lambda l: l.source == 'gstr2b'):
            if line.match_state in ('ignored', 'disputed'):
                continue
            bill = self._find_bill(line, bill_map, date_tol, used_bill_ids=used_bill_ids)
            if not bill:
                line.write({
                    'match_state': 'missing_in_odoo',
                    'move_id': False,
                    'mismatch_detail': _('No posted vendor bill found for this GSTR-2B invoice.'),
                    'diff_taxable_value': line.taxable_value,
                    'diff_cgst': line.cgst_amount,
                    'diff_sgst': line.sgst_amount,
                    'diff_igst': line.igst_amount,
                    'diff_cess': line.cess_amount,
                })
                continue

            used_bill_ids.add(bill.id)
            diffs = self._amount_diffs(line, bill)
            mismatch_fields = []
            for field_name, label in [
                ('diff_taxable_value', 'Taxable'),
                ('diff_cgst', 'CGST'),
                ('diff_sgst', 'SGST'),
                ('diff_igst', 'IGST'),
                ('diff_cess', 'Cess'),
            ]:
                if float_compare(abs(diffs[field_name]), amount_tol, precision_digits=prec) > 0:
                    mismatch_fields.append('%s (%.2f)' % (label, diffs[field_name]))

            vals = {
                'move_id': bill.id,
                'partner_id': bill.partner_id.id,
                **diffs,
            }
            if mismatch_fields:
                vals.update({
                    'match_state': 'mismatch',
                    'mismatch_detail': _('Amount mismatch: %s') % ', '.join(mismatch_fields),
                })
            else:
                vals.update({
                    'match_state': 'matched',
                    'mismatch_detail': False,
                })
            line.write(vals)

        # Bills in period with no 2B counterpart
        Gap = self.env['armora.gst.gstr2b.line']
        gap_vals = []
        for bill in bills:
            if bill.id in used_bill_ids:
                continue
            tax = self._bill_tax_amounts(bill)
            gap_vals.append({
                'reconciliation_id': reconciliation.id,
                'source': 'odoo',
                'match_state': 'missing_in_2b',
                'move_id': bill.id,
                'partner_id': bill.partner_id.id,
                'vendor_gstin': bill.partner_id.vat,
                'vendor_name': bill.partner_id.display_name,
                'invoice_number': bill.ref or bill.name,
                'invoice_date': bill.invoice_date,
                'document_type': 'credit_note' if bill.move_type == 'in_refund' else 'invoice',
                'taxable_value': tax['taxable_value'],
                'cgst_amount': tax['cgst_amount'],
                'sgst_amount': tax['sgst_amount'],
                'igst_amount': tax['igst_amount'],
                'cess_amount': tax['cess_amount'],
                'invoice_value': abs(bill.amount_total_signed),
                'mismatch_detail': _('Posted vendor bill not found in imported GSTR-2B data.'),
            })
        if gap_vals:
            Gap.create(gap_vals)
        return True

    @api.model
    def _period_vendor_bills(self, reconciliation):
        return self.env['account.move'].search([
            ('company_id', '=', reconciliation.company_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('invoice_date', '>=', reconciliation.period_start),
            ('invoice_date', '<=', reconciliation.period_end),
            ('country_code', '=', 'IN'),
        ])

    @api.model
    def _earlier_vendor_bills(self, reconciliation):
        """Posted bills dated before the period from suppliers present in the 2B data."""
        gstins = {
            (gstin or '').upper().strip()
            for gstin in reconciliation.line_ids.filtered(lambda l: l.source == 'gstr2b').mapped('vendor_gstin')
        } - {''}
        if not gstins:
            return self.env['account.move']
        return self.env['account.move'].search([
            ('company_id', '=', reconciliation.company_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('invoice_date', '<', reconciliation.period_start),
            ('country_code', '=', 'IN'),
            ('partner_id.vat', 'in', list(gstins)),
        ])

    @api.model
    def _index_bills(self, bills):
        """Index by normalized GSTIN + invoice number.

        Bills whose vendor has no GSTIN go under an empty GSTIN key so a 2B line
        can still find them; bills of a known vendor are never offered to a
        different supplier GSTIN.
        """
        Line = self.env['armora.gst.gstr2b.line']
        index = {}
        for bill in bills:
            gstin = (bill.partner_id.vat or '').upper().strip()
            number = Line.normalize_invoice_number(bill.ref or bill.name)
            key = (gstin, number)
            index.setdefault(key, self.env['account.move'])
            index[key] |= bill
        return index

    @api.model
    def _find_bill(self, line, bill_map, date_tol, used_bill_ids=None):
        Line = self.env['armora.gst.gstr2b.line']
        used_bill_ids = used_bill_ids or set()
        gstin = (line.vendor_gstin or '').upper().strip()
        number = Line.normalize_invoice_number(line.invoice_number)
        candidates = bill_map.get((gstin, number), self.env['account.move'])
        if not candidates and gstin:
            candidates = bill_map.get(('', number), self.env['account.move'])
        if used_bill_ids:
            candidates = candidates.filtered(lambda b: b.id not in used_bill_ids)
        if not candidates:
            return self.env['account.move']

        # Prefer credit notes to refunds and invoices to vendor bills.
        want_refund = (line.document_type or '') == 'credit_note'
        typed = candidates.filtered(
            lambda b: (b.move_type == 'in_refund') == want_refund
        )
        if typed:
            candidates = typed

        def _date_ok(bill):
            if not line.invoice_date or not bill.invoice_date:
                return True
            delta = abs((bill.invoice_date - line.invoice_date).days)
            return delta <= date_tol

        filtered = candidates.filtered(_date_ok)
        if not filtered:
            # Outside date tolerance: treat as missing in Odoo (do not fall back).
            return self.env['account.move']
        # Prefer exact GSTIN + closest date
        return filtered.sorted(
            key=lambda b: abs((b.invoice_date - line.invoice_date).days) if (b.invoice_date and line.invoice_date) else 999
        )[:1]

    @api.model
    def _bill_tax_amounts(self, bill):
        """Return GST amounts in company currency for consistent 2B comparison."""
        company_currency = bill.company_id.currency_id
        taxable = 0.0
        cgst = sgst = igst = cess = 0.0
        for line in bill.invoice_line_ids.filtered(
            lambda l: l.display_type in (False, 'product') and not l.tax_line_id
        ):
            # balance is always company currency; price_subtotal is document currency.
            taxable += abs(line.balance)
        # Reverse charge taxes post a +100% and a -100% tax line (net zero);
        # skip the offsetting line so the tax is counted once, as in GSTR-2B.
        for tax_line in bill.line_ids.filtered(
            lambda l: l.tax_line_id and not (l.tax_repartition_line_id.factor_percent < 0)
        ):
            tax = tax_line.tax_line_id
            amount = abs(tax_line.balance)
            name = (tax.name or '').upper()
            tax_type = getattr(tax, 'l10n_in_gst_tax_type', False) or ''
            if tax_type == 'cgst' or 'CGST' in name:
                cgst += amount
            elif tax_type == 'sgst' or 'SGST' in name or 'UTGST' in name:
                sgst += amount
            elif tax_type == 'igst' or 'IGST' in name:
                igst += amount
            elif tax_type == 'cess' or 'CESS' in name:
                cess += amount
        money = self.env['armora.gst.money'].round_amount
        return {
            'taxable_value': money(taxable, company_currency),
            'cgst_amount': money(cgst, company_currency),
            'sgst_amount': money(sgst, company_currency),
            'igst_amount': money(igst, company_currency),
            'cess_amount': money(cess, company_currency),
        }

    @api.model
    def _amount_diffs(self, line, bill):
        tax = self._bill_tax_amounts(bill)
        money = self.env['armora.gst.money'].round_amount
        currency = line.currency_id
        return {
            'diff_taxable_value': money((line.taxable_value or 0.0) - tax['taxable_value'], currency),
            'diff_cgst': money((line.cgst_amount or 0.0) - tax['cgst_amount'], currency),
            'diff_sgst': money((line.sgst_amount or 0.0) - tax['sgst_amount'], currency),
            'diff_igst': money((line.igst_amount or 0.0) - tax['igst_amount'], currency),
            'diff_cess': money((line.cess_amount or 0.0) - tax['cess_amount'], currency),
        }
