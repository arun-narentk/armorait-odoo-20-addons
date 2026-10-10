# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.l10n_in_ewaybill.tools.ewaybill_api import EWayBillApi

_logger = logging.getLogger(__name__)


class ArmoraGstEwaybillCloseService(models.AbstractModel):
    """Voluntary EWB Closure API service.

    Endpoint path is read from company config (not hard-coded beyond default).
    Official IAP/GSP path must match current sandbox specs before production use.
    """

    _name = 'armora.gst.ewaybill.close.service'
    _description = 'Armora GST E-Way Bill Closure Service'

    @api.model
    def _get_environment(self, company):
        if company.armora_gst_api_environment:
            return company.armora_gst_api_environment
        return 'production' if company.l10n_in_edi_production_env else 'sandbox'

    @api.model
    def validate_closure(self, record, ewb_number, closure_date, remarks):
        company = record.company_id
        if not company.armora_gst_enable_ewaybill_closure:
            raise UserError(_('Voluntary E-Way Bill closure is disabled in company settings.'))
        if not self.env['armora.gst.rule'].rule_applies(
            'EWB_CLOSURE',
            on_date=closure_date or fields.Date.context_today(self),
        ):
            raise UserError(_('EWB closure rule is not effective for the selected date.'))
        if not ewb_number:
            raise ValidationError(_('E-Way Bill number is required for closure.'))
        if not closure_date:
            raise ValidationError(_('Closure date is required.'))
        if not (remarks or '').strip():
            raise ValidationError(_('Closure remarks are required.'))

        status = getattr(record, 'armora_ewb_status', False) or 'active'
        if status in ('cancelled', 'discarded'):
            raise UserError(_('Cannot close a cancelled or discarded E-Way Bill.'))
        if status == 'closed' or getattr(record, 'armora_ewb_closure_status', False) == 'closed':
            raise UserError(_('This E-Way Bill is already closed.'))
        if getattr(record, 'armora_ewb_closure_requested', False) and getattr(record, 'armora_ewb_closure_status', False) == 'requested':
            raise UserError(_('A closure request is already in progress for this E-Way Bill.'))

        gen_date = getattr(record, 'armora_ewb_generation_date', False)
        if gen_date:
            gen_day = fields.Datetime.context_timestamp(record, gen_date).date() if hasattr(gen_date, 'hour') else fields.Date.to_date(gen_date)
            if closure_date < gen_day:
                raise ValidationError(_('Closure date cannot be before the E-Way Bill generation date.'))

        validity = getattr(record, 'armora_ewb_validity_date', False)
        rule = self.env['armora.gst.rule'].find_applicable('EWB_CLOSURE', on_date=closure_date)
        post_expiry_days = 0
        if rule:
            post_expiry_days = int(rule.get_config().get('post_expiry_window_days') or 0)
        if validity:
            valid_day = fields.Datetime.context_timestamp(record, validity).date() if hasattr(validity, 'hour') else fields.Date.to_date(validity)
            if closure_date > valid_day + timedelta(days=post_expiry_days):
                raise ValidationError(_(
                    'Closure date is outside EWB validity (and any configured post-expiry window).'
                ))

        delivery_status = getattr(record, 'armora_ewb_delivery_status', False)
        if delivery_status and delivery_status != 'delivered':
            # Advisory: closure should happen after delivery; block in blocking modes
            mode = company.armora_gst_validation_mode or 'blocking'
            if mode in ('blocking', 'strict'):
                raise UserError(_(
                    'E-Way Bill closure should happen after delivery. '
                    'Set Delivery Status (EWB) to Delivered before closing, '
                    'or adjust validation mode.'
                ))
        return True

    @api.model
    def _build_payload(self, ewb_number, closure_date, remarks):
        return {
            'ewbNo': str(ewb_number),
            'closedDate': fields.Date.to_date(closure_date).strftime('%d/%m/%Y'),
            'remarks': (remarks or '').strip(),
        }

    @api.model
    def _call_close_api(self, company, payload):
        """Call configured closure endpoint via Odoo IAP connector when available.

        Returns a normalized dict: {success, data, error, error_code, retryable}
        """
        url_path = company.armora_gst_ewaybill_close_path or '/iap/l10n_in_edi_ewaybill/1/close'
        is_production = self._get_environment(company) == 'production'
        params = {
            'json_payload': payload,
            'username': company.sudo().l10n_in_ewaybill_username,
            'gstin': company.vat,
        }
        try:
            if not EWayBillApi(company)._ewaybill_check_authentication():
                return {
                    'success': False,
                    'error_code': 'auth',
                    'error': _('E-Way Bill authentication failed.'),
                    'retryable': True,
                }
        except Exception as err:
            _logger.info('EWB auth probe failed: %s', err)

        try:
            response = self.env['iap.account']._l10n_in_connect_to_server(
                is_production=is_production,
                params=params,
                url_path=url_path,
                config_parameter='l10n_in_edi_ewaybill.endpoint',
                timeout=70,
            )
        except Exception as err:
            _logger.warning('EWB closure API call failed: %s', err)
            return {
                'success': False,
                'error_code': 'timeout',
                'error': _('GSTN / GSP unavailable or request timed out: %s') % err,
                'retryable': True,
                'raw': {'exception': str(err)},
            }

        if not isinstance(response, dict):
            return {
                'success': False,
                'error_code': 'schema',
                'error': _('Unexpected closure API response schema.'),
                'retryable': True,
                'raw': response,
            }
        if response.get('error'):
            errors = response.get('error') or []
            first = errors[0] if errors else {}
            code = str(first.get('code') or 'api_error')
            message = first.get('message') or str(errors)
            retryable = code in ('404', 'timeout', 'waiting', '503', 'auth', '238')
            # Duplicate / already closed style codes (best-effort; confirm vs official specs)
            if code in ('already_closed', 'duplicate', '312'):
                retryable = False
            return {
                'success': False,
                'error_code': code,
                'error': message,
                'retryable': retryable,
                'raw': response,
            }
        return {
            'success': True,
            'data': response.get('data') or response,
            'raw': response,
            'retryable': False,
        }

    @api.model
    def action_close_ewaybill(self, record, ewb_number, closure_date, remarks, delivery_date=None):
        """Validate and submit voluntary EWB closure. Idempotent against duplicate requests."""
        if delivery_date and hasattr(record, 'armora_ewb_delivery_status'):
            # Do not flip stock delivery; only EWB operational marker if still pending.
            # Applied before validation, which requires a delivered EWB in blocking mode.
            if record.armora_ewb_delivery_status == 'pending':
                record.armora_ewb_delivery_status = 'delivered'
        self.validate_closure(record, ewb_number, closure_date, remarks)
        company = record.company_id
        payload = self._build_payload(ewb_number, closure_date, remarks)

        record.write({
            'armora_ewb_closure_requested': True,
            'armora_ewb_closure_status': 'requested',
            'armora_ewb_closure_date': closure_date,
            'armora_ewb_closure_remarks': remarks,
            'armora_ewb_closure_user_id': self.env.user.id,
            'armora_ewb_closure_error': False,
        })

        result = self._call_close_api(company, payload)
        audit_vals = {
            'company_id': company.id,
            'gstin': company.vat,
            'document_model': record._name,
            'document_res_id': record.id,
            'document_name': getattr(record, 'name', False) or getattr(record, 'display_name', False),
            'api_type': 'ewaybill_close',
            'api_environment': self._get_environment(company),
            'request_reference': ewb_number,
            'request_payload': payload,
            'response_payload': result.get('raw') or result,
            'success': bool(result.get('success')),
            'error_code': result.get('error_code'),
            'error_message': result.get('error'),
        }

        if result.get('success'):
            data = result.get('data') or {}
            record.write({
                'armora_ewb_status': 'closed',
                'armora_ewb_closure_status': 'closed',
                'armora_ewb_closure_timestamp': fields.Datetime.now(),
                'armora_ewb_closure_response': str(data),
                'armora_ewb_closure_api_reference': data.get('reference') or data.get('ackNo') or ewb_number,
                'armora_ewb_closure_error': False,
            })
            if hasattr(record, 'message_post'):
                record.message_post(body=_(
                    'E-Way Bill %(ewb)s closed voluntarily on %(date)s. Remarks: %(remarks)s',
                    ewb=ewb_number,
                    date=closure_date,
                    remarks=remarks,
                ))
            audit = self.env['armora.gst.api.audit'].log_api(audit_vals)
            return {'success': True, 'audit_id': audit.id, 'data': data}

        record.write({
            'armora_ewb_closure_status': 'failed',
            'armora_ewb_closure_error': result.get('error'),
            'armora_ewb_closure_response': str(result.get('raw') or result),
            # Keep requested flag False on failure so user can retry (unless duplicate)
            'armora_ewb_closure_requested': result.get('error_code') in ('already_closed', 'duplicate'),
        })
        if result.get('error_code') in ('already_closed', 'duplicate'):
            record.write({
                'armora_ewb_status': 'closed',
                'armora_ewb_closure_status': 'closed',
                'armora_ewb_closure_timestamp': fields.Datetime.now(),
            })
        if hasattr(record, 'message_post'):
            record.message_post(body=_(
                'E-Way Bill closure failed [%(code)s]: %(msg)s',
                code=result.get('error_code'),
                msg=result.get('error'),
            ))
        audit = self.env['armora.gst.api.audit'].log_api(audit_vals)
        return {
            'success': False,
            'audit_id': audit.id,
            'error_code': result.get('error_code'),
            'error': result.get('error'),
            'retryable': result.get('retryable'),
        }
