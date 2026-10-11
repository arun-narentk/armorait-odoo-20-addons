# -*- coding: utf-8 -*-
import io

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from odoo import _, fields, models

LINE_COLUMNS = [
    ('Match Status', 22),
    ('Source', 12),
    ('Vendor GSTIN', 18),
    ('Vendor Name', 30),
    ('Invoice No.', 18),
    ('Invoice Date', 13),
    ('Type', 13),
    ('Place of Supply', 16),
    ('Reverse Charge', 10),
    ('ITC Available', 12),
    ('Taxable Value', 15),
    ('IGST', 13),
    ('CGST', 13),
    ('SGST', 13),
    ('Cess', 11),
    ('Invoice Value', 15),
    ('Vendor Bill', 20),
    ('Diff Taxable', 13),
    ('Diff IGST', 12),
    ('Diff CGST', 12),
    ('Diff SGST', 12),
    ('Mismatch Detail', 45),
    ('Notes', 30),
    ('Supplier GSTR-1', 14),
    ('GSTR-1 Filed On', 14),
    ('GSTR-1 Period', 12),
    ('Supplier GSTR-3B', 14),
]

DATE_COLUMNS = (5, 24)

BUCKET_SHEETS = [
    ('mismatch', 'Mismatch'),
    ('missing_in_odoo', 'Missing in Odoo'),
    ('missing_in_2b', 'Missing in 2B'),
]


class ArmoraGstGstr2b(models.Model):
    _inherit = 'armora.gst.gstr2b'

    def action_export_excel(self):
        """Build the reconciliation workbook, attach it to the record and download it."""
        self.ensure_one()
        content = self._armora_build_reconciliation_xlsx()
        filename = '%s.xlsx' % _(
            '%(statement)s Reconciliation %(gstin)s %(fy)s-%(period)s',
            statement=self._statement_label(), gstin=self.gstin, fy=self.financial_year, period=self.return_period,
        )
        # Keep one export per reconciliation: a new export replaces the previous file.
        Attachment = self.env['ir.attachment']
        attachment = Attachment.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('name', '=', filename),
        ], limit=1)
        vals = {
            'name': filename,
            'raw': content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        if attachment:
            attachment.write(vals)
        else:
            attachment = Attachment.create(vals)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'download',
        }

    def _armora_build_reconciliation_xlsx(self):
        self.ensure_one()
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {'in_memory': True})
        styles = {
            'title': book.add_format({'bold': True, 'font_size': 15, 'font_color': '#0F172A'}),
            'label': book.add_format({'bold': True, 'font_color': '#475569'}),
            'header': book.add_format({
                'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1A73E8',
                'border': 1, 'text_wrap': True, 'valign': 'vcenter',
            }),
            'text': book.add_format({'border': 1}),
            'date': book.add_format({'border': 1, 'num_format': 'dd-mm-yyyy'}),
            'money': book.add_format({'border': 1, 'num_format': '#,##0.00'}),
            'money_bold': book.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00', 'bg_color': '#EEF4FD'}),
            'bold': book.add_format({'border': 1, 'bold': True, 'bg_color': '#EEF4FD'}),
            'int': book.add_format({'border': 1, 'num_format': '0'}),
            'int_bold': book.add_format({'border': 1, 'bold': True, 'num_format': '0', 'bg_color': '#EEF4FD'}),
        }
        self._armora_write_summary_sheet(book, styles)
        self._armora_write_lines_sheet(book, styles, _('All Lines'), self.line_ids)
        for state, label in BUCKET_SHEETS:
            self._armora_write_lines_sheet(
                book, styles, label, self.line_ids.filtered(lambda l, s=state: l.match_state == s),
            )
        book.close()
        return output.getvalue()

    def _armora_write_summary_sheet(self, book, styles):
        sheet = book.add_worksheet(_('Summary'))
        sheet.set_column(0, 0, 26)
        sheet.set_column(1, 6, 16)
        sheet.write(0, 0, _('%s Reconciliation Summary', self._statement_label()), styles['title'])
        state_label = dict(self._fields['state']._description_selection(self.env)).get(self.state)
        info = [
            (_('Company'), self.company_id.name),
            (_('GSTIN'), self.gstin),
            (_('Financial Year'), self.financial_year),
            (_('Return Period'), self.return_period),
            (_('Status'), state_label),
            (_('Matched On'), fields.Datetime.to_string(
                fields.Datetime.context_timestamp(self, self.matched_at),
            ) if self.matched_at else '-'),
        ]
        for row, (label, value) in enumerate(info, start=2):
            sheet.write(row, 0, label, styles['label'])
            sheet.write(row, 1, value or '')

        row = len(info) + 3
        headers = [_('Bucket'), _('Lines'), _('Taxable Value'), _('IGST'), _('CGST'), _('SGST'), _('Cess')]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, styles['header'])
        labels = dict(self.env['armora.gst.gstr2b.line']._fields['match_state']._description_selection(self.env))
        first = row + 1
        for state, label in labels.items():
            lines = self.line_ids.filtered(lambda l, s=state: l.match_state == s)
            row += 1
            sheet.write(row, 0, label, styles['text'])
            sheet.write(row, 1, len(lines), styles['int'])
            for col, fname in enumerate(('taxable_value', 'igst_amount', 'cgst_amount', 'sgst_amount', 'cess_amount'), start=2):
                sheet.write(row, col, sum(lines.mapped(fname)), styles['money'])
        row += 1
        sheet.write(row, 0, _('Total'), styles['bold'])
        sheet.write_formula(row, 1, '=SUM(B%d:B%d)' % (first + 1, row), styles['int_bold'])
        for col in range(2, 7):
            letter = xl_col_to_name(col)
            sheet.write_formula(row, col, '=SUM(%s%d:%s%d)' % (letter, first + 1, letter, row), styles['money_bold'])

        row += 2
        sheet.write(row, 0, _('ITC in %s', self._statement_label()), styles['label'])
        sheet.write(row, 1, self.amount_itc_total, styles['money'])
        sheet.write(row + 1, 0, _('ITC matched'), styles['label'])
        sheet.write(row + 1, 1, self.amount_matched, styles['money'])
        sheet.write(row + 2, 0, _('ITC at risk (mismatch)'), styles['label'])
        sheet.write(row + 2, 1, self.amount_mismatch, styles['money'])
        sheet.write(row + 3, 0, _('ITC missing in Odoo'), styles['label'])
        sheet.write(row + 3, 1, self.amount_missing_odoo, styles['money'])

    def _armora_write_lines_sheet(self, book, styles, title, lines):
        sheet = book.add_worksheet(title[:31])
        for col, (header, width) in enumerate(LINE_COLUMNS):
            sheet.write(0, col, header, styles['header'])
            sheet.set_column(col, col, width)
        sheet.set_row(0, 30)
        sheet.freeze_panes(1, 0)
        Line = self.env['armora.gst.gstr2b.line']
        selections = {
            fname: dict(Line._fields[fname]._description_selection(self.env))
            for fname in ('match_state', 'source', 'document_type', 'itc_availability',
                          'supplier_filing_status', 'supplier_3b_status')
        }
        for row, line in enumerate(lines, start=1):
            values = [
                selections['match_state'].get(line.match_state, ''),
                selections['source'].get(line.source, ''),
                line.vendor_gstin or '',
                line.vendor_name or line.partner_id.name or '',
                line.invoice_number or '',
                line.invoice_date,
                selections['document_type'].get(line.document_type, ''),
                line.place_of_supply or '',
                _('Yes') if line.reverse_charge else _('No'),
                selections['itc_availability'].get(line.itc_availability, ''),
                line.taxable_value,
                line.igst_amount,
                line.cgst_amount,
                line.sgst_amount,
                line.cess_amount,
                line.invoice_value,
                line.move_id.name or '',
                line.diff_taxable_value,
                line.diff_igst,
                line.diff_cgst,
                line.diff_sgst,
                line.mismatch_detail or '',
                line.notes or '',
                selections['supplier_filing_status'].get(line.supplier_filing_status, ''),
                line.supplier_filing_date,
                line.supplier_filing_period or '',
                selections['supplier_3b_status'].get(line.supplier_3b_status, ''),
            ]
            for col, value in enumerate(values):
                if col in DATE_COLUMNS:
                    if value:
                        sheet.write_datetime(row, col, fields.Datetime.to_datetime(value), styles['date'])
                    else:
                        sheet.write_blank(row, col, None, styles['text'])
                elif isinstance(value, float):
                    sheet.write_number(row, col, value, styles['money'])
                else:
                    sheet.write_string(row, col, str(value), styles['text'])
        if lines:
            sheet.autofilter(0, 0, len(lines), len(LINE_COLUMNS) - 1)
