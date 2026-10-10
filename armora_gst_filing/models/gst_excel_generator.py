# -*- coding: utf-8 -*-
import io
import json
import re
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.binary import BinaryBytes

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    load_workbook = None


class ArmoraGstExcelGenerator(models.AbstractModel):
    """Populate an official GSTN Returns Offline Tool workbook from filing lines.

    Output is for import into the GSTN Returns Offline Tool. That tool then
    generates the JSON uploaded to the GST Portal (not a direct portal upload).
    """

    _name = 'armora.gst.excel.generator'
    _description = 'Armora GSTN Offline Tool Excel Generator'

    @api.model
    def generate(self, filing):
        filing.ensure_one()
        if filing.validation_error_count:
            raise UserError(_(
                'Cannot generate the GST upload file while blocking validation errors exist.'
            ))
        if filing.validation_status == 'pending':
            raise UserError(_('Validate the filing before generating the GST upload file.'))
        if filing.state in ('submitted', 'filed', 'cancelled'):
            filing._raise_readonly()
        if load_workbook is None:
            raise UserError(_('Python package openpyxl is required to generate the GST upload file.'))

        template = filing.template_id or self.env['armora.gst.excel.template'].get_active_template(
            filing.company_id, filing.filing_type, on_date=filing.period_end
        )
        if not template or not template.template_file:
            raise UserError(_(
                'Upload and activate an official GSTN Returns Offline Tool Excel template '
                'before generating the GST upload file.'
            ))

        mapping = {}
        if template.mapping_json:
            try:
                mapping = json.loads(template.mapping_json)
            except json.JSONDecodeError as err:
                raise UserError(_('Template mapping_json is invalid JSON: %s') % err) from err

        data = template.template_file.content
        wb = load_workbook(filename=io.BytesIO(data), data_only=False)
        section_sheets = self._section_sheet_map(mapping, wb.sheetnames)

        generators = {
            'b2b': self._generate_b2b,
            'b2cl': self._generate_b2cl,
            'b2cs': self._generate_b2cs,
            'exp': self._generate_export,
            'cdnr': self._generate_cdnr,
            'cdnur': self._generate_cdnur,
            'hsn_b2b': self._generate_hsn_b2b,
            'hsn_b2c': self._generate_hsn_b2c,
            'nil': self._generate_nil,
            'docs': self._generate_docs,
        }
        for section, method in generators.items():
            sheet_name = section_sheets.get(section)
            if not sheet_name or sheet_name not in wb.sheetnames:
                continue
            meta = mapping.get(sheet_name) or {}
            method(wb[sheet_name], filing, meta)

        buffer = io.BytesIO()
        wb.save(buffer)
        content = BinaryBytes(buffer.getvalue())
        if filing.period_start:
            period_label = filing.period_start.strftime('%B_%Y')
        else:
            period_label = (filing.return_period or filing.name or 'period').replace('/', '-')
        gstin_label = (filing.gstin or 'GSTIN').replace('/', '-')
        filename = 'GSTR1_%s_%s.xlsx' % (period_label, gstin_label)
        filing.write({
            'generated_file': content,
            'generated_filename': filename,
            'generated_at': fields.Datetime.now(),
            'generated_by': self.env.user.id,
            'template_id': template.id,
            'template_version': template.version,
            'state': 'generated',
        })
        return True

    @api.model
    def _section_sheet_map(self, mapping, sheetnames):
        result = {}
        for sheet_name, meta in (mapping or {}).items():
            section = meta.get('logical_section')
            if section and sheet_name in sheetnames:
                result[section] = sheet_name
        if not result:
            # Fallback: guess from sheet names only
            Template = self.env['armora.gst.excel.template']
            for sheet_name in sheetnames:
                section = Template._guess_logical_section(sheet_name, [])
                if section and section not in result:
                    result[section] = sheet_name
        # Legacy templates mapped only one HSN sheet to hsn_b2b.
        if 'hsn_b2b' in result and 'hsn_b2c' not in result:
            for sheet_name in sheetnames:
                key = (sheet_name or '').strip().lower().replace(' ', '')
                if key in ('hsnb2c', 'hsn(b2c)'):
                    result['hsn_b2c'] = sheet_name
                    break
        return result

    @api.model
    def _header_index(self, headers):
        idx = {}
        for i, header in enumerate(headers or []):
            if not header:
                continue
            key = self._normalize_header(header)
            idx[key] = i
        return idx

    @api.model
    def _normalize_header(self, header):
        return re.sub(r'[^a-z0-9]+', '', str(header).strip().lower())

    @api.model
    def _find_col(self, header_idx, *aliases):
        for alias in aliases:
            key = self._normalize_header(alias)
            if key in header_idx:
                return header_idx[key]
        # partial contains
        for alias in aliases:
            key = self._normalize_header(alias)
            for h, i in header_idx.items():
                if key and key in h:
                    return i
        return None

    @api.model
    def _clear_data_rows(self, ws, header_row, max_clear=5000):
        """Clear value cells below header without removing template rows/formulas above."""
        for row in ws.iter_rows(min_row=header_row + 1, max_row=header_row + max_clear):
            empty = True
            for cell in row:
                if cell.value not in (None, ''):
                    empty = False
                    # Keep formula cells in template footer if any far below; stop early when long empty stretch
                    if isinstance(cell.value, str) and cell.value.startswith('='):
                        continue
                    cell.value = None
            if empty:
                # allow scanning further but stop after consecutive empties handled by max_clear
                pass

    @api.model
    def _write_row(self, ws, row_idx, values_by_col):
        for col_idx, value in values_by_col.items():
            if col_idx is None:
                continue
            cell = ws.cell(row=row_idx, column=col_idx + 1)
            # Avoid overwriting formulas in unexpected places
            if isinstance(cell.value, str) and cell.value.startswith('='):
                continue
            if isinstance(value, str):
                cell.value = value
                cell.number_format = '@'
            elif isinstance(value, (date, datetime)):
                cell.value = value
            elif isinstance(value, (int, float)):
                cell.value = value
            else:
                cell.value = value

    @api.model
    def _as_text(self, value):
        if value in (None, False):
            return ''
        return str(value)

    @api.model
    def _as_date(self, value):
        return value if value else None

    @api.model
    def _format_export_type(self, export_type):
        key = (export_type or '').lower()
        return {
            'wpay': 'WPAY',
            'wopay': 'WOPAY',
            'expwp': 'EXPWP',
            'expwop': 'EXPWOP',
        }.get(key, (export_type or '').upper())

    @api.model
    def _lines(self, filing, gst_table):
        return filing.line_ids.filtered(lambda l: l.gst_table == gst_table)

    @api.model
    def _rate_key(self, rate):
        """Stable bucket key for GST rate (avoids float dict-key noise)."""
        return round(float(rate or 0.0), 3)

    @api.model
    def _invoice_rate_buckets(self, lines):
        """Group snapshot lines by document + GST rate for Offline Tool sheets.

        GSTN GSTR-1 B2B/CDNR/EXP sheets expect one row per invoice (or note)
        per tax rate, not a single rolled-up invoice row.
        """
        buckets = {}
        for line in lines:
            doc_key = line.move_id.id or (line.invoice_number, line.invoice_date)
            key = (doc_key, self._rate_key(line.gst_rate))
            bucket = buckets.setdefault(key, {
                'gstin': line.partner_gstin,
                'receiver': line.partner_name,
                'invoice_number': line.invoice_number,
                'invoice_date': line.invoice_date,
                'invoice_value': line.invoice_value,
                'pos': line.place_of_supply_code,
                'reverse': 'Y' if line.is_reverse_charge else 'N',
                'invoice_type': 'Regular',
                'document_type': line.document_type,
                'export_type': line.export_type,
                'port_code': line.port_code,
                'shipping_bill_number': line.shipping_bill_number,
                'shipping_bill_date': line.shipping_bill_date,
                'supply_type': line.supply_type,
                'is_export': line.is_export,
                'original_invoice_number': line.original_invoice_number,
                'original_invoice_date': line.original_invoice_date,
                'rate': line.gst_rate or 0.0,
                'taxable': 0.0,
                'cgst': 0.0,
                'sgst': 0.0,
                'igst': 0.0,
                'cess': 0.0,
            })
            bucket['taxable'] += line.taxable_value or 0.0
            bucket['cgst'] += line.cgst_amount or 0.0
            bucket['sgst'] += line.sgst_amount or 0.0
            bucket['igst'] += line.igst_amount or 0.0
            bucket['cess'] += line.cess_amount or 0.0
        return buckets

    @api.model
    def _cdnur_ur_type(self, line_or_bucket):
        """Map CDNUR rows to Offline Tool UR Type values."""
        supply_type = getattr(line_or_bucket, 'get', None)
        if callable(supply_type):
            supply = line_or_bucket.get('supply_type')
            is_export = line_or_bucket.get('is_export')
            export_type = (line_or_bucket.get('export_type') or '').upper()
        else:
            supply = line_or_bucket.supply_type
            is_export = line_or_bucket.is_export
            export_type = (line_or_bucket.export_type or '').upper()
        if supply == 'b2cl':
            return 'B2CL'
        if is_export or supply == 'export':
            if export_type in ('WPAY', 'WOPAY', 'EXPWP', 'EXPWOP'):
                return 'EXPWP' if export_type in ('WPAY', 'EXPWP') else 'EXPWOP'
            return 'EXPWOP'
        return 'B2CL'

    def _generate_b2b(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        headers = meta.get('headers') or []
        idx = self._header_index(headers)
        self._clear_data_rows(ws, header_row)
        row = header_row + 1
        for data in self._invoice_rate_buckets(self._lines(filing, 'b2b')).values():
            values = {
                self._find_col(idx, 'GSTIN/UIN of Recipient', 'GSTIN of Recipient', 'GSTIN'): self._as_text(data['gstin']),
                self._find_col(idx, 'Receiver Name', 'Name'): self._as_text(data['receiver']),
                self._find_col(idx, 'Invoice Number', 'Invoice No'): self._as_text(data['invoice_number']),
                self._find_col(idx, 'Invoice date', 'Invoice Date'): self._as_date(data['invoice_date']),
                self._find_col(idx, 'Invoice Value'): data['invoice_value'],
                self._find_col(idx, 'Place Of Supply', 'Place of Supply'): self._as_text(data['pos']),
                self._find_col(idx, 'Reverse Charge'): data['reverse'],
                self._find_col(idx, 'Invoice Type'): data['invoice_type'],
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
                self._find_col(idx, 'Central Tax Paid', 'CGST'): data['cgst'],
                self._find_col(idx, 'State/UT Tax Paid', 'SGST'): data['sgst'],
                self._find_col(idx, 'Cess Paid', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_b2cl(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        row = header_row + 1
        for data in self._invoice_rate_buckets(self._lines(filing, 'b2cl')).values():
            values = {
                self._find_col(idx, 'Invoice Number', 'Invoice No'): self._as_text(data['invoice_number']),
                self._find_col(idx, 'Invoice date', 'Invoice Date'): self._as_date(data['invoice_date']),
                self._find_col(idx, 'Invoice Value'): data['invoice_value'],
                self._find_col(idx, 'Place Of Supply', 'Place of Supply'): self._as_text(data['pos']),
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
                self._find_col(idx, 'Cess Paid', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_b2cs(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        # Aggregate by POS + rate + supply type
        buckets = {}
        for line in self._lines(filing, 'b2cs'):
            key = (line.place_of_supply_code, line.gst_rate, 'E' if line.is_export else 'OE')
            bucket = buckets.setdefault(key, {
                'type': key[2],
                'pos': line.place_of_supply_code,
                'rate': line.gst_rate,
                'taxable': 0.0,
                'cgst': 0.0,
                'sgst': 0.0,
                'igst': 0.0,
                'cess': 0.0,
            })
            bucket['taxable'] += line.taxable_value or 0.0
            bucket['cgst'] += line.cgst_amount or 0.0
            bucket['sgst'] += line.sgst_amount or 0.0
            bucket['igst'] += line.igst_amount or 0.0
            bucket['cess'] += line.cess_amount or 0.0
        row = header_row + 1
        for data in buckets.values():
            values = {
                self._find_col(idx, 'Type'): data['type'],
                self._find_col(idx, 'Place Of Supply', 'Place of Supply'): self._as_text(data['pos']),
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
                self._find_col(idx, 'Central Tax Paid', 'CGST'): data['cgst'],
                self._find_col(idx, 'State/UT Tax Paid', 'SGST'): data['sgst'],
                self._find_col(idx, 'Cess Paid', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_export(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        row = header_row + 1
        for data in self._invoice_rate_buckets(self._lines(filing, 'exp')).values():
            values = {
                self._find_col(idx, 'Export Type', 'Type'): self._format_export_type(data['export_type']),
                self._find_col(idx, 'Invoice Number', 'Invoice No'): self._as_text(data['invoice_number']),
                self._find_col(idx, 'Invoice date', 'Invoice Date'): self._as_date(data['invoice_date']),
                self._find_col(idx, 'Invoice Value'): data['invoice_value'],
                self._find_col(idx, 'Port Code'): self._as_text(data['port_code']),
                self._find_col(idx, 'Shipping Bill Number', 'Shipping Bill No'): self._as_text(data['shipping_bill_number']),
                self._find_col(idx, 'Shipping Bill Date'): self._as_date(data['shipping_bill_date']),
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_cdnr(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        row = header_row + 1
        for data in self._invoice_rate_buckets(self._lines(filing, 'cdnr')).values():
            values = {
                self._find_col(idx, 'GSTIN/UIN of Recipient', 'GSTIN'): self._as_text(data['gstin']),
                self._find_col(idx, 'Receiver Name', 'Name'): self._as_text(data['receiver']),
                self._find_col(idx, 'Note Number', 'Credit Note No', 'Invoice Number'): self._as_text(data['invoice_number']),
                self._find_col(idx, 'Note Date', 'Credit Note Date', 'Invoice Date'): self._as_date(data['invoice_date']),
                self._find_col(idx, 'Note Type', 'Document Type'): 'C' if data['document_type'] == 'credit_note' else 'D',
                self._find_col(idx, 'Original Invoice Number', 'Original Note Number'): self._as_text(data['original_invoice_number']),
                self._find_col(idx, 'Original Invoice Date', 'Original Note Date'): self._as_date(data['original_invoice_date']),
                self._find_col(idx, 'Place Of Supply', 'Place of Supply'): self._as_text(data['pos']),
                self._find_col(idx, 'Reverse Charge'): data['reverse'],
                self._find_col(idx, 'Note Value', 'Invoice Value'): data['invoice_value'],
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
                self._find_col(idx, 'Central Tax Paid', 'CGST'): data['cgst'],
                self._find_col(idx, 'State/UT Tax Paid', 'SGST'): data['sgst'],
                self._find_col(idx, 'Cess Paid', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_cdnur(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        row = header_row + 1
        for data in self._invoice_rate_buckets(self._lines(filing, 'cdnur')).values():
            values = {
                self._find_col(idx, 'UR Type', 'Type'): self._cdnur_ur_type(data),
                self._find_col(idx, 'Note Number', 'Invoice Number'): self._as_text(data['invoice_number']),
                self._find_col(idx, 'Note Date', 'Invoice Date'): self._as_date(data['invoice_date']),
                self._find_col(idx, 'Note Type'): 'C' if data['document_type'] == 'credit_note' else 'D',
                self._find_col(idx, 'Place Of Supply', 'Place of Supply'): self._as_text(data['pos']),
                self._find_col(idx, 'Note Value', 'Invoice Value'): data['invoice_value'],
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Paid', 'IGST'): data['igst'],
                self._find_col(idx, 'Cess Paid', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_hsn_rows(self, ws, filing, meta, gst_tables):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        buckets = {}
        lines = filing.line_ids.filtered(
            lambda l: l.gst_table in gst_tables and (l.hsn_code or l.sac_code)
        )
        for line in lines:
            hsn = line.hsn_code or line.sac_code or ''
            key = (hsn, line.gst_rate, line.uom)
            bucket = buckets.setdefault(key, {
                'hsn': hsn,
                'description': line.description,
                'uom': line.uom,
                'qty': 0.0,
                'rate': line.gst_rate,
                'taxable': 0.0,
                'cgst': 0.0,
                'sgst': 0.0,
                'igst': 0.0,
                'cess': 0.0,
            })
            # HSN summary is net of credit notes, which snapshot lines keep positive.
            sign = -1 if line.document_type == 'credit_note' else 1
            bucket['qty'] += sign * (line.quantity or 0.0)
            bucket['taxable'] += sign * (line.taxable_value or 0.0)
            bucket['cgst'] += sign * (line.cgst_amount or 0.0)
            bucket['sgst'] += sign * (line.sgst_amount or 0.0)
            bucket['igst'] += sign * (line.igst_amount or 0.0)
            bucket['cess'] += sign * (line.cess_amount or 0.0)
        row = header_row + 1
        for data in buckets.values():
            values = {
                self._find_col(idx, 'HSN', 'HSN/SAC'): self._as_text(data['hsn']),
                self._find_col(idx, 'Description'): self._as_text(data['description']),
                self._find_col(idx, 'UQC', 'UOM'): self._as_text(data['uom']),
                self._find_col(idx, 'Total Quantity', 'Quantity'): data['qty'],
                self._find_col(idx, 'Rate'): data['rate'],
                self._find_col(idx, 'Taxable Value', 'Total Value'): data['taxable'],
                self._find_col(idx, 'Integrated Tax Amount', 'IGST'): data['igst'],
                self._find_col(idx, 'Central Tax Amount', 'CGST'): data['cgst'],
                self._find_col(idx, 'State/UT Tax Amount', 'SGST'): data['sgst'],
                self._find_col(idx, 'Cess Amount', 'Cess'): data['cess'],
            }
            self._write_row(ws, row, values)
            row += 1

    def _generate_hsn_b2b(self, ws, filing, meta):
        self._generate_hsn_rows(ws, filing, meta, ('b2b', 'cdnr'))

    def _generate_hsn_b2c(self, ws, filing, meta):
        self._generate_hsn_rows(ws, filing, meta, ('b2cl', 'b2cs', 'exp', 'cdnur'))

    def _generate_nil(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        buckets = {
            'nil_rated': 0.0,
            'exempt': 0.0,
            'non_gst': 0.0,
        }
        for line in self._lines(filing, 'nil'):
            key = line.supply_type if line.supply_type in buckets else 'nil_rated'
            buckets[key] += line.taxable_value or 0.0
        row = header_row + 1
        if any(buckets.values()):
            values = {
                self._find_col(idx, 'Nil Rated Supplies', 'Nil Rated'): buckets['nil_rated'],
                self._find_col(idx, 'Exempted', 'Exempt'): buckets['exempt'],
                self._find_col(idx, 'Non-GST Supplies', 'Non GST'): buckets['non_gst'],
            }
            clean = {c: v for c, v in values.items() if c is not None}
            self._write_row(ws, row, clean)

    def _generate_docs(self, ws, filing, meta):
        header_row = meta.get('header_row') or 1
        idx = self._header_index(meta.get('headers') or [])
        self._clear_data_rows(ws, header_row)
        docs = {
            'Invoices for outward supply': filing.line_ids.filtered(lambda l: l.document_type == 'invoice' and l.gst_table in ('b2b', 'b2cl', 'b2cs', 'exp')),
            'Credit Note': filing.line_ids.filtered(lambda l: l.document_type == 'credit_note'),
            'Debit Note': filing.line_ids.filtered(lambda l: l.document_type == 'debit_note'),
        }
        row = header_row + 1
        for nature, lines in docs.items():
            moves = lines.mapped('move_id')
            numbers = sorted(set(moves.mapped('name')))
            values = {
                self._find_col(idx, 'Nature of Document', 'Document Type'): nature,
                self._find_col(idx, 'Sr. No. From', 'From'): numbers[0] if numbers else '',
                self._find_col(idx, 'Sr. No. To', 'To'): numbers[-1] if numbers else '',
                self._find_col(idx, 'Total Number', 'Total'): len(numbers),
                self._find_col(idx, 'Cancelled'): 0,
            }
            self._write_row(ws, row, values)
            row += 1
