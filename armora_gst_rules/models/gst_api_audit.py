# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models


class ArmoraGstApiAudit(models.Model):
    """Audit trail for GST API operations. Never stores credentials."""

    _name = 'armora.gst.api.audit'
    _description = 'Armora GST API Audit'
    _order = 'request_timestamp desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    request_timestamp = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', required=True, index=True)
    gstin = fields.Char()
    document_model = fields.Char()
    document_res_id = fields.Integer()
    document_name = fields.Char()
    api_type = fields.Selection(
        selection=[
            ('einvoice_generate', 'E-Invoice Generate'),
            ('einvoice_cancel', 'E-Invoice Cancel'),
            ('ewaybill_generate', 'E-Way Bill Generate'),
            ('ewaybill_by_irn', 'E-Way Bill by IRN'),
            ('ewaybill_cancel', 'E-Way Bill Cancel'),
            ('ewaybill_close', 'E-Way Bill Close'),
            ('ewaybill_vehicle', 'E-Way Bill Vehicle Update'),
            ('ewaybill_extend', 'E-Way Bill Extend Validity'),
            ('other', 'Other'),
        ],
        required=True,
        index=True,
    )
    api_environment = fields.Selection(
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        required=True,
        default='sandbox',
    )
    request_reference = fields.Char()
    response_reference = fields.Char()
    success = fields.Boolean(default=False, index=True)
    error_code = fields.Char()
    error_message = fields.Text()
    request_payload = fields.Text(
        help='Sanitized request payload. Secrets must never be written here.',
    )
    response_payload = fields.Text(
        help='Sanitized response payload.',
    )
    retry_count = fields.Integer(default=0)
    notes = fields.Char()

    @api.depends('api_type', 'document_name', 'request_timestamp')
    def _compute_name(self):
        for rec in self:
            stamp = fields.Datetime.to_string(rec.request_timestamp) if rec.request_timestamp else ''
            rec.name = '%s / %s / %s' % (rec.api_type or '', rec.document_name or '', stamp)

    @api.model
    def _sanitize_payload(self, payload):
        """Drop known secret keys recursively."""
        secret_keys = {
            'password', 'pwd', 'auth_token', 'token', 'otp', 'apikey', 'api_key',
            'client_secret', 'secret', 'authorization', 'refresh_token',
        }
        if payload is None:
            return None
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                return payload
        if isinstance(payload, dict):
            cleaned = {}
            for key, value in payload.items():
                if str(key).lower() in secret_keys:
                    cleaned[key] = '***REDACTED***'
                else:
                    cleaned[key] = self._sanitize_payload(value)
            return cleaned
        if isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload]
        return payload

    @api.model
    def log_api(self, vals):
        data = dict(vals or {})
        if 'request_payload' in data:
            sanitized = self._sanitize_payload(data.get('request_payload'))
            data['request_payload'] = (
                json.dumps(sanitized, default=str) if not isinstance(sanitized, str) else sanitized
            )
        if 'response_payload' in data:
            sanitized = self._sanitize_payload(data.get('response_payload'))
            data['response_payload'] = (
                json.dumps(sanitized, default=str) if not isinstance(sanitized, str) else sanitized
            )
        data.setdefault('user_id', self.env.user.id)
        data.setdefault('company_id', self.env.company.id)
        # Audit writes are system trail entries; callers may lack create ACL.
        return self.sudo().create(data)
