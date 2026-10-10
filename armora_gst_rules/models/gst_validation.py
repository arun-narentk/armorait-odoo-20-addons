# -*- coding: utf-8 -*-
import re

from odoo import api, models, _


class ArmoraGstValidation(models.AbstractModel):
    """Reusable pre-API GST validation service.

    Categories: GSTIN, STATE_CODE, PIN_CODE, SHIP_TO, BILL_TO, EXPORT, EWB, IRN, TAX, DOCUMENT
    Severity: error (blocks), warning (shown; blocks only when required), info
    """

    _name = 'armora.gst.validation'
    _description = 'Armora GST Validation Engine'

    PIN_RE = re.compile(r'^[1-9][0-9]{5}$')
    STATE_CODE_RE = re.compile(r'^[0-9]{2}$')

    @api.model
    def _result(self, code, severity, message, model=None, record_id=None, field_name=None, category=None):
        return {
            'code': code,
            'severity': severity,
            'message': message,
            'model': model,
            'record_id': record_id,
            'field_name': field_name,
            'category': category or code.split('_')[0] if code else 'DOCUMENT',
        }

    @api.model
    def has_blocking_errors(self, results, block_on_warning=False):
        for item in results or []:
            if item.get('severity') == 'error':
                return True
            if block_on_warning and item.get('severity') == 'warning':
                return True
        return False

    @api.model
    def format_messages(self, results, severities=('error', 'warning')):
        lines = []
        for item in results or []:
            if item.get('severity') in severities:
                lines.append('[%s] %s' % (item.get('severity', '').upper(), item.get('message')))
        return '\n'.join(lines)

    @api.model
    def normalize_gstin(self, value):
        return self.env['armora.gst.gstin.validator'].normalize(value)

    @api.model
    def validate_gstin_value(self, value, field_name='gstin', model=None, record_id=None, allow_urp=False):
        results = []
        raw = self.normalize_gstin(value)
        if allow_urp and raw == 'URP':
            return results
        check = self.env['armora.gst.gstin.validator'].validate(raw)
        if check['status'] == 'invalid':
            results.append(self._result(
                'GSTIN_INVALID',
                'error',
                check['message'],
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='GSTIN',
            ))
        elif check['status'] == 'warning':
            results.append(self._result(
                'GSTIN_STATE_UNKNOWN',
                'warning',
                check['message'],
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='GSTIN',
            ))
        return results

    @api.model
    def validate_state_code(self, state_code, field_name='state_code', model=None, record_id=None):
        results = []
        code = (state_code or '').strip()
        if not code:
            results.append(self._result(
                'STATE_CODE_MISSING',
                'error',
                _('State code is required.'),
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='STATE_CODE',
            ))
            return results
        if not self.STATE_CODE_RE.match(code):
            results.append(self._result(
                'STATE_CODE_INVALID',
                'error',
                _('State code %s is invalid. Use a 2-digit GST state code.') % code,
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='STATE_CODE',
            ))
            return results
        if code not in ('96', '97'):
            State = self.env['res.country.state']
            tin_state = State.search([
                ('country_id.code', '=', 'IN'),
                ('l10n_in_tin', '=', code),
            ], limit=1)
            if not tin_state:
                results.append(self._result(
                    'STATE_CODE_UNKNOWN',
                    'warning',
                    _('GST state code %s is not found in Odoo Indian states.') % code,
                    model=model,
                    record_id=record_id,
                    field_name=field_name,
                    category='STATE_CODE',
                ))
        return results

    @api.model
    def validate_pin_code(self, pin_code, field_name='zip', model=None, record_id=None, required=False):
        results = []
        pin = ''.join(ch for ch in str(pin_code or '') if ch.isdigit())
        if not pin:
            if required:
                results.append(self._result(
                    'PIN_CODE_MISSING',
                    'error',
                    _('PIN code is required.'),
                    model=model,
                    record_id=record_id,
                    field_name=field_name,
                    category='PIN_CODE',
                ))
            return results
        if not self.PIN_RE.match(pin):
            results.append(self._result(
                'PIN_CODE_INVALID',
                'error',
                _('PIN code is invalid. Expected a 6-digit Indian PIN (not starting with 0).'),
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='PIN_CODE',
            ))
        return results

    @api.model
    def validate_gstin_state_match(
        self,
        gstin,
        state_code,
        field_name='state_code',
        model=None,
        record_id=None,
        allow_urp=False,
    ):
        results = []
        raw = self.normalize_gstin(gstin)
        code = (state_code or '').strip()
        if allow_urp and raw == 'URP':
            return results
        if not raw or not code:
            return results
        if len(raw) >= 2 and raw[:2] != code:
            results.append(self._result(
                'GSTIN_STATE_MISMATCH',
                'error',
                _('Ship-to GSTIN state code does not match the supplied state code.'),
                model=model,
                record_id=record_id,
                field_name=field_name,
                category='STATE_CODE',
            ))
        return results

    @api.model
    def validate_bill_to_ship_to_distinct(
        self,
        bill_to_gstin,
        ship_to_gstin,
        model=None,
        record_id=None,
        on_date=None,
    ):
        results = []
        if not self.env['armora.gst.rule'].rule_applies('EINV_BILLTO_NE_SHIPTO', on_date=on_date):
            return results
        bill = self.normalize_gstin(bill_to_gstin)
        ship = self.normalize_gstin(ship_to_gstin)
        if bill and ship and bill != 'URP' and ship != 'URP' and bill == ship:
            results.append(self._result(
                'BILL_SHIP_GSTIN_SAME',
                'error',
                _('Bill-to GSTIN and Ship-to GSTIN must be distinct for Bill-to/Ship-to transactions.'),
                model=model,
                record_id=record_id,
                field_name='ship_to_gstin',
                category='SHIP_TO',
            ))
        return results

    @api.model
    def validate_ship_to_gstin_required(
        self,
        ship_details_present,
        ewb_required,
        ship_to_gstin,
        model=None,
        record_id=None,
        on_date=None,
    ):
        """GSTN Aug 2026: ShipDtls.Gstin conditionally mandatory when ship details + EWB."""
        results = []
        Rule = self.env['armora.gst.rule']
        if not Rule.rule_applies('EINV_SHIP_TO_GSTIN_REQUIRED', on_date=on_date):
            return results
        if not (ship_details_present and ewb_required):
            return results
        raw = self.normalize_gstin(ship_to_gstin)
        if not raw:
            results.append(self._result(
                'SHIP_TO_GSTIN_REQUIRED',
                'error',
                _(
                    'Ship-to GSTIN is required when shipping details are provided '
                    'and E-Way Bill generation is required.'
                ),
                model=model,
                record_id=record_id,
                field_name='ship_to_gstin',
                category='SHIP_TO',
            ))
        return results

    @api.model
    def validate_export_ship_details(self, exp_ship_dtls, model=None, record_id=None, on_date=None):
        """EWB-by-IRN ExpShipDtls.Gstin mandatory from Aug 2026."""
        results = []
        Rule = self.env['armora.gst.rule']
        if not Rule.rule_applies('EINV_EXPORT_SHIP_GSTIN', on_date=on_date):
            return results
        details = exp_ship_dtls or {}
        gstin = self.normalize_gstin(details.get('Gstin') or details.get('GSTIN'))
        if not gstin:
            results.append(self._result(
                'EXP_SHIP_GSTIN_REQUIRED',
                'error',
                _('GSTIN under ExpShipDtls is mandatory for E-Way Bill by IRN (use URP where applicable).'),
                model=model,
                record_id=record_id,
                field_name='exp_ship_gstin',
                category='EXPORT',
            ))
            return results
        results.extend(self.validate_gstin_value(
            gstin,
            field_name='exp_ship_gstin',
            model=model,
            record_id=record_id,
            allow_urp=True,
        ))
        if details.get('Stcd'):
            results.extend(self.validate_state_code(
                details.get('Stcd'),
                field_name='exp_ship_state',
                model=model,
                record_id=record_id,
            ))
            results.extend(self.validate_gstin_state_match(
                gstin,
                details.get('Stcd'),
                field_name='exp_ship_state',
                model=model,
                record_id=record_id,
                allow_urp=True,
            ))
        if 'Pin' in details or 'PIN' in details:
            pin = details.get('Pin') if 'Pin' in details else details.get('PIN')
            results.extend(self.validate_pin_code(
                pin,
                field_name='exp_ship_pin',
                model=model,
                record_id=record_id,
                required=True,
            ))
        return results

    @api.model
    def validate_context(self, context):
        """Run a bundle of validations from a plain dict context.

        Expected keys (all optional except as rules require):
        bill_to_gstin, ship_to_gstin, ship_to_state, ship_to_pin,
        ship_details_present, ewb_required, is_export, exp_ship_dtls,
        document_date, model, record_id
        """
        ctx = context or {}
        model = ctx.get('model')
        record_id = ctx.get('record_id')
        on_date = ctx.get('document_date')
        results = []

        if ctx.get('bill_to_gstin'):
            results.extend(self.validate_gstin_value(
                ctx.get('bill_to_gstin'),
                field_name='bill_to_gstin',
                model=model,
                record_id=record_id,
                allow_urp=bool(ctx.get('bill_to_allow_urp')),
            ))

        results.extend(self.validate_ship_to_gstin_required(
            ship_details_present=bool(ctx.get('ship_details_present')),
            ewb_required=bool(ctx.get('ewb_required')),
            ship_to_gstin=ctx.get('ship_to_gstin'),
            model=model,
            record_id=record_id,
            on_date=on_date,
        ))

        if ctx.get('ship_to_gstin') or (ctx.get('ship_details_present') and ctx.get('ewb_required')):
            if ctx.get('ship_to_gstin'):
                results.extend(self.validate_gstin_value(
                    ctx.get('ship_to_gstin'),
                    field_name='ship_to_gstin',
                    model=model,
                    record_id=record_id,
                    allow_urp=True,
                ))
                if ctx.get('bill_to_gstin'):
                    results.extend(self.validate_bill_to_ship_to_distinct(
                        ctx.get('bill_to_gstin'),
                        ctx.get('ship_to_gstin'),
                        model=model,
                        record_id=record_id,
                        on_date=on_date,
                    ))
                if ctx.get('ship_to_state'):
                    results.extend(self.validate_state_code(
                        ctx.get('ship_to_state'),
                        field_name='ship_to_state',
                        model=model,
                        record_id=record_id,
                    ))
                    results.extend(self.validate_gstin_state_match(
                        ctx.get('ship_to_gstin'),
                        ctx.get('ship_to_state'),
                        field_name='ship_to_state',
                        model=model,
                        record_id=record_id,
                        allow_urp=True,
                    ))
            if ctx.get('ship_to_pin') is not None or ctx.get('ship_details_present'):
                pin_required = bool(ctx.get('ship_details_present') and ctx.get('ewb_required'))
                if ctx.get('ship_to_pin') is not None or pin_required:
                    results.extend(self.validate_pin_code(
                        ctx.get('ship_to_pin'),
                        field_name='ship_to_pin',
                        model=model,
                        record_id=record_id,
                        required=pin_required,
                    ))

        if ctx.get('is_export') and ctx.get('exp_ship_dtls') is not None:
            results.extend(self.validate_export_ship_details(
                ctx.get('exp_ship_dtls'),
                model=model,
                record_id=record_id,
                on_date=on_date,
            ))

        return results
