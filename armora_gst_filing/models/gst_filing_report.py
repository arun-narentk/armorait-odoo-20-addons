# -*- coding: utf-8 -*-
from odoo import _, models

GSTR1_SECTIONS = [
    ('b2b', 'B2B Invoices (Table 4)'),
    ('b2cl', 'B2C Large Invoices (Table 5)'),
    ('b2cs', 'B2C Small (Table 7)'),
    ('exp', 'Exports (Table 6)'),
    ('cdnr', 'Credit / Debit Notes - Registered (Table 9B)'),
    ('cdnur', 'Credit / Debit Notes - Unregistered (Table 9B)'),
    ('nil', 'Nil Rated, Exempt and Non-GST (Table 8)'),
]

AMOUNT_FIELDS = ('taxable_value', 'igst_amount', 'cgst_amount', 'sgst_amount', 'cess_amount', 'total_tax')


class ArmoraGstFiling(models.Model):
    _inherit = 'armora.gst.filing'

    def _get_gstr1_report_data(self):
        """Section-wise and HSN-wise totals of the snapshot lines for the summary PDF."""
        self.ensure_one()
        Line = self.env['armora.gst.filing.line']
        domain = [('filing_id', '=', self.id)]
        aggregates = ['invoice_number:count_distinct', '__count'] + ['%s:sum' % f for f in AMOUNT_FIELDS]

        by_table = {
            table: (docs, count, *amounts)
            for table, docs, count, *amounts in Line._read_group(domain, ['gst_table'], aggregates)
        }
        sections = []
        for key, label in GSTR1_SECTIONS:
            docs, count, *amounts = by_table.get(key, (0, 0) + (0.0,) * len(AMOUNT_FIELDS))
            row = dict(zip(AMOUNT_FIELDS, amounts))
            row.update({
                'key': key,
                'label': label,
                'documents': count if key == 'b2cs' else docs,
            })
            sections.append(row)

        # Table 12 is net of credit notes, which the snapshot keeps positive.
        hsn_totals = {}
        groupby = ['hsn_code', 'sac_code', 'gst_rate', 'uom', 'document_type']
        hsn_aggregates = ['quantity:sum'] + ['%s:sum' % f for f in AMOUNT_FIELDS]
        hsn_domain = domain + ['|', ('hsn_code', '!=', False), ('sac_code', '!=', False), ('gst_table', '!=', 'nil')]
        for hsn_code, sac_code, rate, uom, document_type, qty, *amounts in Line._read_group(
            hsn_domain, groupby, hsn_aggregates, order='hsn_code, sac_code, gst_rate',
        ):
            hsn = hsn_code or sac_code
            sign = -1 if document_type == 'credit_note' else 1
            row = hsn_totals.setdefault((hsn, rate, uom), dict(
                dict.fromkeys(AMOUNT_FIELDS, 0.0), hsn=hsn, rate=rate, uom=uom or '', quantity=0.0,
            ))
            row['quantity'] += sign * qty
            for fname, amount in zip(AMOUNT_FIELDS, amounts):
                row[fname] += sign * amount
        hsn_rows = list(hsn_totals.values())

        return {
            'sections': sections,
            'hsn_rows': hsn_rows,
            'net': {
                'taxable_value': self.amount_taxable,
                'igst_amount': self.amount_igst,
                'cgst_amount': self.amount_cgst,
                'sgst_amount': self.amount_sgst,
                'cess_amount': self.amount_cess,
                'total_tax': self.amount_total_tax,
            },
            'state_label': dict(self._fields['state']._description_selection(self.env)).get(self.state),
            'filing_type_label': dict(self._fields['filing_type']._description_selection(self.env)).get(self.filing_type),
        }

    def _get_gstr1_report_filename(self):
        self.ensure_one()
        return _('GSTR-1 Summary - %(gstin)s - %(fy)s-%(period)s', gstin=self.gstin, fy=self.financial_year, period=self.return_period)
