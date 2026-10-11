# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QrRecord(models.Model):
    _name = 'rn.qr.record'
    _description = 'Universal QR Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    token = fields.Char(required=True, index=True, copy=False, tracking=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    model_id = fields.Many2one('ir.model', compute='_compute_model_id', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    template_id = fields.Many2one('rn.qr.template')
    qr_image = fields.Binary(attachment=True, copy=False)
    qr_svg = fields.Text(copy=False)
    qr_url = fields.Char(copy=False)
    active = fields.Boolean(default=True)
    expiration_datetime = fields.Datetime()
    is_expired = fields.Boolean(compute='_compute_is_expired')
    last_generated_at = fields.Datetime(copy=False)
    scan_count = fields.Integer(compute='_compute_scan_stats')
    first_scanned_at = fields.Datetime(compute='_compute_scan_stats')
    last_scanned_at = fields.Datetime(compute='_compute_scan_stats')
    scan_log_ids = fields.One2many('rn.qr.scan.log', 'qr_record_id')

    _rn_qr_record_token_unique = models.Constraint(
        'unique(token)',
        "QR token must be unique.",
    )
    _rn_qr_record_model_res_unique = models.Constraint(
        'unique(res_model, res_id)',
        "Only one QR record is allowed per business record.",
    )

    @api.depends('res_model')
    def _compute_model_id(self):
        model_names = [name for name in set(self.mapped('res_model')) if name]
        model_data = self.env['ir.model'].sudo().search_read([('model', 'in', model_names)], ['model'])
        model_map = {item['model']: item['id'] for item in model_data}
        for record in self:
            record.model_id = model_map.get(record.res_model)

    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = bool(record.expiration_datetime and record.expiration_datetime <= now)

    def _compute_scan_stats(self):
        grouped = self.env['rn.qr.scan.log'].read_group(
            [('qr_record_id', 'in', self.ids)],
            ['qr_record_id'],
            ['__count', 'scan_datetime:min', 'scan_datetime:max'],
        )
        counter = {qr_id: (count, first, last) for qr_id, count, first, last in grouped if qr_id}
        for record in self:
            record.scan_count, record.first_scanned_at, record.last_scanned_at = counter.get(
                record.id, (0, False, False)
            )

    def action_open_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
