# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ArmoraGstExcelTemplateImportWizard(models.TransientModel):
    _name = 'armora.gst.excel.template.import.wizard'
    _description = 'Import GSTN Returns Offline Tool Excel Template'

    name = fields.Char(required=True, default='GSTR-1 Offline Tool Template')
    filing_type = fields.Selection([
        ('gstr1', 'GSTR-1'),
        ('gstr1a', 'GSTR-1A'),
        ('gstr3b', 'GSTR-3B'),
        ('gstr9', 'GSTR-9'),
    ], required=True, default='gstr1')
    version = fields.Char(required=True, default='1')
    financial_year = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    template_file = fields.Binary(
        string='Offline Tool Workbook',
        required=True,
        help='Official Excel template from the GSTN Returns Offline Tool (GSTR-1/IFF).',
    )
    template_filename = fields.Char()
    notes = fields.Text()

    def action_import(self):
        self.ensure_one()
        if not self.template_file:
            raise ValidationError(_(
                'Please upload the official GSTN Returns Offline Tool Excel workbook.'
            ))
        template = self.env['armora.gst.excel.template'].create({
            'name': self.name,
            'filing_type': self.filing_type,
            'version': self.version,
            'financial_year': self.financial_year,
            'company_id': self.company_id.id,
            'template_file': self.template_file,
            'template_filename': self.template_filename,
            'notes': self.notes,
            'active': True,
        })
        template.action_inspect_workbook()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'armora.gst.excel.template',
            'res_id': template.id,
            'view_mode': 'form',
            'target': 'current',
        }
