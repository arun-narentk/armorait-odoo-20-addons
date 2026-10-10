# -*- coding: utf-8 -*-
import csv
import io
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    load_workbook = None


class ArmoraGst2bImportWizard(models.TransientModel):
    _name = 'armora.gst.2b.import.wizard'
    _description = 'Import GSTR-2B Data'

    reconciliation_id = fields.Many2one('armora.gst.gstr2b', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='reconciliation_id.company_id')
    data_file = fields.Binary(string='GSTR-2B File', required=True)
    filename = fields.Char()
    replace_existing = fields.Boolean(
        string='Replace Existing 2B Lines',
        default=True,
        help='Remove previously imported GSTR-2B lines before importing.',
    )
    note = fields.Text(readonly=True, default=lambda self: _(
        'Upload a CSV or Excel export of GSTR-2B B2B invoices.\n'
        'Expected columns (header names, case-insensitive):\n'
        'GSTIN, Invoice Number, Invoice Date, Taxable Value, CGST, SGST, IGST, Cess, Invoice Value, Vendor Name'
    ))

    def action_import(self):
        self.ensure_one()
        rec = self.reconciliation_id
        if rec.state in ('closed', 'cancelled'):
            raise UserError(_('Cannot import into a closed or cancelled reconciliation.'))
        if not self.data_file:
            raise UserError(_('Please upload a GSTR-2B file.'))

        raw = self.data_file.content
        rows = self._parse_file(raw, self.filename or '')
        if not rows:
            raise UserError(_('No data rows found in the uploaded file.'))

        if self.replace_existing:
            rec.line_ids.filtered(lambda l: l.source == 'gstr2b').unlink()
            rec.line_ids.filtered(lambda l: l.source == 'odoo').unlink()

        Line = self.env['armora.gst.gstr2b.line']
        vals_list = []
        for row in rows:
            gstin = (row.get('gstin') or '').strip().upper()
            invoice_number = (row.get('invoice_number') or '').strip()
            if not invoice_number and not gstin:
                continue
            vals_list.append({
                'reconciliation_id': rec.id,
                'source': 'gstr2b',
                'match_state': 'pending',
                'vendor_gstin': gstin or False,
                'vendor_name': row.get('vendor_name') or False,
                'invoice_number': invoice_number or False,
                'invoice_date': row.get('invoice_date'),
                'taxable_value': row.get('taxable_value') or 0.0,
                'cgst_amount': row.get('cgst') or 0.0,
                'sgst_amount': row.get('sgst') or 0.0,
                'igst_amount': row.get('igst') or 0.0,
                'cess_amount': row.get('cess') or 0.0,
                'invoice_value': row.get('invoice_value') or 0.0,
                'document_type': row.get('document_type') or 'invoice',
            })
        if not vals_list:
            raise UserError(_('Could not map any invoice rows. Check column headers.'))
        Line.create(vals_list)
        rec.state = 'imported'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'armora.gst.gstr2b',
            'res_id': rec.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _parse_file(self, raw, filename):
        name = (filename or '').lower()
        if name.endswith('.csv') or (not name.endswith('.xlsx') and not name.endswith('.xls')):
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')
            return self._rows_from_csv(text)
        if load_workbook is None:
            raise UserError(_('Python package openpyxl is required to import Excel files.'))
        try:
            wb = load_workbook(filename=io.BytesIO(raw), read_only=True, data_only=True)
        except Exception as err:
            raise UserError(_('Unable to open Excel file: %s') % err) from err
        # GST portal GSTR-2B workbook: "Read me" first, invoices on "B2B",
        # notes on "B2B-CDNR". A plain one-sheet export uses the active sheet.
        sheets = [ws for ws in wb.worksheets if self._normalize_header(ws.title) in ('b2b', 'b2bcdnr')]
        rows = []
        for ws in sheets or [wb.active]:
            rows.extend(self._rows_from_sheet(ws))
        return rows

    @api.model
    def _rows_from_sheet(self, ws):
        """Parse one sheet whose header row may sit below a title block.

        The portal file has a two-row header (e.g. "Invoice Details" over
        "Invoice number"); the second row is merged in when its GSTIN cell is empty.
        """
        all_rows = list(ws.iter_rows(values_only=True))
        header_idx = None
        gstin_col = None
        for i, row in enumerate(all_rows[:20]):
            for col, cell in enumerate(row or ()):
                if 'gstin' in self._normalize_header(cell):
                    header_idx, gstin_col = i, col
                    break
            if header_idx is not None:
                break
        if header_idx is None:
            return []
        headers = list(all_rows[header_idx])
        start = header_idx + 1
        if start < len(all_rows):
            sub = list(all_rows[start] or ())
            if gstin_col >= len(sub) or sub[gstin_col] in (None, ''):
                width = max(len(headers), len(sub))
                headers += [None] * (width - len(headers))
                sub += [None] * (width - len(sub))
                headers = [s if s not in (None, '') else h for h, s in zip(headers, sub)]
                start += 1
        return self._rows_from_header_values(headers, all_rows[start:])

    @api.model
    def _rows_from_csv(self, text):
        reader = csv.reader(io.StringIO(text))
        try:
            headers = next(reader)
        except StopIteration:
            return []
        return self._rows_from_header_values(headers, reader)

    @api.model
    def _normalize_header(self, header):
        return ''.join(ch for ch in str(header or '').lower() if ch.isalnum())

    @api.model
    def _rows_from_header_values(self, headers, rows_iter):
        header_idx = {}
        for i, header in enumerate(headers or []):
            key = self._normalize_header(header)
            if key:
                header_idx[key] = i

        def col(*aliases):
            for alias in aliases:
                key = self._normalize_header(alias)
                if key in header_idx:
                    return header_idx[key]
                for h, i in header_idx.items():
                    if key and key in h:
                        return i
            return None

        mapping = {
            'gstin': col('GSTIN', 'GSTIN of Supplier', 'Supplier GSTIN'),
            'vendor_name': col(
                'Trade/Legal Name', 'Trade Name', 'Legal Name', 'Vendor Name', 'Supplier Name', 'Name',
            ),
            'invoice_number': col('Invoice Number', 'Invoice No', 'Note Number', 'Document Number'),
            'invoice_date': col('Invoice Date', 'Note Date', 'Document Date'),
            'taxable_value': col('Taxable Value', 'Taxable Amount'),
            'cgst': col('CGST', 'Central Tax'),
            'sgst': col('SGST', 'State/UT Tax', 'State Tax', 'UTGST'),
            'igst': col('IGST', 'Integrated Tax'),
            'cess': col('Cess', 'Cess Amount'),
            'invoice_value': col('Invoice Value', 'Note Value', 'Total Invoice Value'),
            'document_type': col('Note Type', 'Document Type'),
        }
        result = []
        for row in rows_iter:
            if not row or all(v in (None, '') for v in row):
                continue
            parsed = {}
            for field, idx in mapping.items():
                if idx is None or idx >= len(row):
                    parsed[field] = False if field in ('gstin', 'vendor_name', 'invoice_number', 'invoice_date', 'document_type') else 0.0
                    continue
                value = row[idx]
                if field == 'invoice_date':
                    parsed[field] = self._parse_date(value)
                elif field == 'document_type':
                    parsed[field] = self._parse_document_type(value)
                elif field in ('gstin', 'vendor_name', 'invoice_number'):
                    parsed[field] = str(value).strip() if value not in (None, '') else False
                else:
                    parsed[field] = self._parse_float(value)
            if parsed.get('invoice_number') or parsed.get('gstin'):
                result.append(parsed)
        return result

    @api.model
    def _parse_document_type(self, value):
        """Map 2B note type ('Credit Note', 'C', 'Debit Note', 'D') to the line selection."""
        text = str(value or '').strip().lower()
        if text in ('c', 'cr') or 'credit' in text:
            return 'credit_note'
        if text in ('d', 'dr') or 'debit' in text:
            return 'debit_note'
        return 'invoice'

    @api.model
    def _parse_float(self, value):
        if value in (None, ''):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(',', '').strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

    @api.model
    def _parse_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day') and not isinstance(value, datetime):
            return value
        text = str(value).strip()
        for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%b-%Y', '%d/%m/%y'):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return False
