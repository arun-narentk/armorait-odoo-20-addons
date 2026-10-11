# -*- coding: utf-8 -*-
import logging

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_ship_to_gstin = fields.Char(
        string='Ship-to GSTIN',
        compute='_compute_rn_ship_fields',
        store=True,
        readonly=False,
        tracking=True,
        help='Ship-to GSTIN for Bill-to/Ship-to. Use URP for unregistered consignees where allowed.',
    )
    rn_ship_to_state_code = fields.Char(
        string='Ship-to State Code',
        compute='_compute_rn_ship_fields',
        store=True,
        readonly=False,
    )
    rn_ship_to_pin = fields.Char(
        string='Ship-to PIN',
        compute='_compute_rn_ship_fields',
        store=True,
        readonly=False,
    )
    rn_ship_to_trade_name = fields.Char(
        string='Ship-to Trade Name',
        help='Optional TrdNm for ExpShipDtls / ship details.',
    )
    rn_exp_ship_gstin = fields.Char(
        string='Export Ship GSTIN',
        help='ExpShipDtls.Gstin for E-Way Bill by IRN on export flows. URP allowed where applicable.',
    )
    rn_exp_ship_trade_name = fields.Char(string='Export Ship Trade Name')
    rn_exp_ship_state_code = fields.Char(string='Export Ship State Code')
    rn_exp_ship_pin = fields.Char(string='Export Ship PIN')
    rn_ewb_required = fields.Boolean(
        string='E-Way Bill Required',
        help='Set when EWB generation is intended with / after IRN.',
    )
    rn_ship_details_locked = fields.Boolean(
        string='Ship Details Locked',
        copy=False,
        tracking=True,
        help='For B2B/SEZ, ship details provided at IRN cannot be replaced later (GSTN Aug 2026).',
    )
    rn_irn = fields.Char(string='IRN', compute='_compute_rn_edi_status', store=False)
    rn_irn_status = fields.Char(string='IRN Status', compute='_compute_rn_edi_status')
    rn_einvoice_status = fields.Char(string='E-Invoice Status', compute='_compute_rn_edi_status')
    rn_ewb_status_display = fields.Char(string='Odoo EWB Status', compute='_compute_rn_edi_status')
    rn_gst_validation_summary = fields.Text(
        string='GST Validation',
        compute='_compute_rn_gst_validation_summary',
    )

    @api.depends(
        'partner_shipping_id',
        'partner_shipping_id.vat',
        'partner_shipping_id.state_id',
        'partner_shipping_id.state_id.l10n_in_tin',
        'partner_shipping_id.zip',
        'partner_id',
        'partner_id.vat',
    )
    def _compute_rn_ship_fields(self):
        Validator = self.env['rn.gst.gstin.validator']
        for move in self:
            # Always assign stored computed fields. Skipping assignment when locked
            # lets Odoo fall back to False and wipe ship details after IRN.
            if move.rn_ship_details_locked:
                move.rn_ship_to_gstin = move.rn_ship_to_gstin
                move.rn_ship_to_state_code = move.rn_ship_to_state_code
                move.rn_ship_to_pin = move.rn_ship_to_pin
                continue
            ship = move.partner_shipping_id or move.partner_id
            if ship:
                move.rn_ship_to_gstin = Validator.normalize(ship.vat) if ship.vat else move.rn_ship_to_gstin
                move.rn_ship_to_state_code = (
                    ship.state_id.l10n_in_tin if ship.state_id else move.rn_ship_to_state_code
                )
                move.rn_ship_to_pin = ship.zip or move.rn_ship_to_pin
            else:
                move.rn_ship_to_gstin = move.rn_ship_to_gstin
                move.rn_ship_to_state_code = move.rn_ship_to_state_code
                move.rn_ship_to_pin = move.rn_ship_to_pin

    def _compute_rn_edi_status(self):
        for move in self:
            irn = False
            einv_state = move.l10n_in_edi_status or 'none'
            ewb_state = move.l10n_in_ewaybill_ids[:1].state or 'none'
            try:
                data = move._get_l10n_in_edi_response_json() or {}
                if isinstance(data, dict):
                    irn = data.get('Irn')
            except Exception:
                irn = False
            move.rn_irn = irn or False
            move.rn_irn_status = 'generated' if irn else einv_state
            move.rn_einvoice_status = einv_state
            move.rn_ewb_status_display = ewb_state

    def _compute_rn_gst_validation_summary(self):
        for move in self:
            results = move._rn_run_einvoice_validations()
            move.rn_gst_validation_summary = self.env['rn.gst.rule.validation'].format_messages(results) or False

    def _rn_ship_details_present(self):
        self.ensure_one()
        if self._rn_is_same_party_shipping():
            return False
        ship = self.partner_shipping_id
        buyer = self.partner_id
        if ship and buyer and ship != buyer:
            return True
        # Manual ship GSTIN + pin/state count even without a distinct delivery partner.
        if self.rn_ship_to_gstin and (self.rn_ship_to_pin or self.rn_ship_to_state_code):
            return True
        return False

    def _rn_is_same_party_shipping(self):
        """True when goods go to the buyer's own registration (same business, same GSTIN).

        The ship-to fields are filled from the customer by default, so without this
        check every ordinary invoice was treated as a Bill-to/Ship-to transaction.
        """
        self.ensure_one()
        Validator = self.env['rn.gst.gstin.validator']
        buyer = self.partner_id
        ship = self.partner_shipping_id or buyer
        bill_gstin = Validator.normalize(buyer.vat or self.l10n_in_gstin or '')
        ship_gstin = Validator.normalize(self.rn_ship_to_gstin or '')
        if not ship_gstin or ship_gstin == 'URP' or ship_gstin != bill_gstin:
            return False
        return ship.commercial_partner_id == buyer.commercial_partner_id

    def _rn_is_ewb_required(self):
        self.ensure_one()
        if self.rn_ewb_required:
            return True
        # An E-Way Bill record on the invoice indicates EWB intent
        return bool(self.l10n_in_ewaybill_ids.filtered(lambda ewb: ewb.state != 'cancel'))

    def _rn_run_einvoice_validations(self):
        self.ensure_one()
        if not self.company_id.rn_gst_enable_einvoice:
            return []
        Validation = self.env['rn.gst.rule.validation']
        bill_gstin = self.partner_id.vat or self.l10n_in_gstin
        same_party = self._rn_is_same_party_shipping()
        ewb_required = self._rn_is_ewb_required()
        ctx = {
            'model': 'account.move',
            'record_id': self.id,
            'document_date': self.invoice_date or fields.Date.context_today(self),
            'bill_to_gstin': bill_gstin,
            'bill_to_allow_urp': self.l10n_in_gst_treatment in ('overseas', 'consumer'),
            'ship_details_present': not same_party and self._rn_ship_details_present(),
            'ewb_required': ewb_required,
            'ship_to_gstin': self.rn_ship_to_gstin,
            'ship_to_state': self.rn_ship_to_state_code,
            'ship_to_pin': self.rn_ship_to_pin,
            'is_export': self.l10n_in_gst_treatment == 'overseas',
        }
        if same_party:
            # Not a Bill-to/Ship-to transaction: no ship-to checks.
            ctx.update(ship_to_gstin=False, ship_to_state=False, ship_to_pin=None)
        if ctx['is_export'] and ewb_required:
            ctx['exp_ship_dtls'] = {
                'Gstin': self.rn_exp_ship_gstin or self.rn_ship_to_gstin or 'URP',
                'TrdNm': self.rn_exp_ship_trade_name or self.rn_ship_to_trade_name,
                'Stcd': self.rn_exp_ship_state_code or self.rn_ship_to_state_code,
                'Pin': self.rn_exp_ship_pin or self.rn_ship_to_pin,
            }
        return Validation.validate_context(ctx)

    def _rn_assert_einvoice_validations(self):
        mode = self.company_id.rn_gst_validation_mode or 'blocking'
        if mode == 'advisory':
            return
        for move in self:
            results = move._rn_run_einvoice_validations()
            block_warnings = mode == 'strict'
            if self.env['rn.gst.rule.validation'].has_blocking_errors(results, block_on_warning=block_warnings):
                raise UserError(self.env['rn.gst.rule.validation'].format_messages(results))

    def write(self, vals):
        locked_fields = {
            'partner_shipping_id',
            'rn_ship_to_gstin',
            'rn_ship_to_state_code',
            'rn_ship_to_pin',
            'rn_ship_to_trade_name',
            'rn_exp_ship_gstin',
            'rn_exp_ship_trade_name',
            'rn_exp_ship_state_code',
            'rn_exp_ship_pin',
        }
        if locked_fields.intersection(vals):
            for move in self.filtered('rn_ship_details_locked'):
                if move.l10n_in_gst_treatment == 'overseas':
                    # Export: GSTN allows replace while generating EWB by IRN
                    continue
                if not self.env.user.has_group('rn_gst_base.group_rn_gst_administrator'):
                    raise UserError(_(
                        'Ship-to details are locked after IRN generation for B2B/SEZ transactions '
                        '(GSTN Aug 2026). Administrator override is required to change them.'
                    ))
                if not self.env.context.get('rn_unlock_ship_details'):
                    raise AccessError(_(
                        'Ship details are locked. Re-open with administrator override '
                        '(context rn_unlock_ship_details).'
                    ))
        return super().write(vals)

    def _rn_lock_ship_details_after_irn(self):
        Rule = self.env['rn.gst.rule']
        for move in self:
            on_date = move.invoice_date or fields.Date.context_today(move)
            if not Rule.rule_applies('EINV_B2B_SHIP_LOCK', on_date=on_date):
                continue
            if move.l10n_in_gst_treatment in ('regular', 'special_economic_zone', 'deemed_export', 'composition'):
                if move._rn_ship_details_present() and not move.rn_ship_details_locked:
                    move.rn_ship_details_locked = True
                    move.message_post(body=_('Ship-to details locked after IRN generation (B2B/SEZ GSTN rule).'))

    def action_rn_unlock_ship_details(self):
        self.ensure_one()
        if not self.env.user.has_group('rn_gst_base.group_rn_gst_administrator'):
            raise AccessError(_('Only Armora GST Administrators can unlock ship details.'))
        self.with_context(rn_unlock_ship_details=True).write({'rn_ship_details_locked': False})
        self.message_post(body=_('Ship-to details unlocked by administrator override.'))
        return True

    # -------------------------------------------------------------------------
    # l10n_in_edi hooks
    # -------------------------------------------------------------------------

    def _l10n_in_edi_generate_invoice_json(self):
        # Also used to compute l10n_in_edi_content, so only enrich here; the
        # blocking validations run in _l10n_in_edi_send_invoice.
        json_payload = super()._l10n_in_edi_generate_invoice_json()
        if not self.company_id.rn_gst_enable_einvoice:
            return json_payload
        return self._rn_enrich_einvoice_ship_details(json_payload)

    def _rn_enrich_einvoice_ship_details(self, json_payload):
        """Ensure ShipDtls.Gstin / trade name follow Aug 2026 advisory."""
        if 'ShipDtls' in json_payload:
            ship = json_payload['ShipDtls']
            gstin = self.rn_ship_to_gstin or ship.get('GSTIN')
            if gstin:
                ship['GSTIN'] = self.env['rn.gst.gstin.validator'].normalize(gstin)
            if self.rn_ship_to_trade_name:
                ship['TrdNm'] = self.rn_ship_to_trade_name
            if self.rn_ship_to_state_code:
                ship['Stcd'] = self.rn_ship_to_state_code
            if self.rn_ship_to_pin:
                pin_digits = self._l10n_in_extract_digits(self.rn_ship_to_pin)
                if pin_digits:
                    ship['Pin'] = int(pin_digits)
            json_payload['ShipDtls'] = ship
        return json_payload

    def _rn_enrich_ewaybill_by_irn_payload(self, json_payload):
        """Add ExpShipDtls.Gstin / TrdNm for EWB by IRN (mandatory from Aug 2026)."""
        self.ensure_one()
        if not json_payload:
            return json_payload
        is_export = self.l10n_in_gst_treatment == 'overseas'
        # Always send ExpShipDtls.Gstin when ship details exist or export, per advisory field addition.
        if is_export or self._rn_ship_details_present() or self.rn_exp_ship_gstin:
            exp = dict(json_payload.get('ExpShipDtls') or {})
            gstin = (
                self.rn_exp_ship_gstin
                or self.rn_ship_to_gstin
                or exp.get('Gstin')
                or ('URP' if is_export else False)
            )
            if gstin:
                exp['Gstin'] = self.env['rn.gst.gstin.validator'].normalize(gstin)
            trd = self.rn_exp_ship_trade_name or self.rn_ship_to_trade_name or exp.get('TrdNm')
            if trd:
                exp['TrdNm'] = trd
            stcd = self.rn_exp_ship_state_code or self.rn_ship_to_state_code or exp.get('Stcd')
            if stcd:
                exp['Stcd'] = stcd
            pin = self.rn_exp_ship_pin or self.rn_ship_to_pin or exp.get('Pin')
            if pin not in (None, False, ''):
                pin_digits = self._l10n_in_extract_digits(str(pin))
                if pin_digits:
                    exp['Pin'] = int(pin_digits)
            if exp:
                json_payload['ExpShipDtls'] = exp
        return json_payload

    def _rn_einvoice_validation_error(self):
        """Return the blocking validation message, or False when the move can be sent."""
        self.ensure_one()
        if not self.company_id.rn_gst_enable_einvoice:
            return False
        try:
            self._rn_assert_einvoice_validations()
        except UserError as error:
            return error.args[0]
        return False

    def _l10n_in_edi_send_invoice(self):
        if message := self._rn_einvoice_validation_error():
            # Report like the core partner validation, so the send wizard shows it.
            self.l10n_in_edi_error = Markup('<br/>').join(message.split('\n'))
            return {'messages': [message]}
        res = super()._l10n_in_edi_send_invoice()
        if not res and self.l10n_in_edi_status == 'sent':
            # The IRN is already issued by the portal: never lose it because of
            # an Armora follow-up step.
            try:
                with self.env.cr.savepoint():
                    self._rn_after_einvoice_success()
            except Exception:
                _logger.exception('Armora post-IRN steps failed for move %s', self.display_name)
        return res

    def _rn_after_einvoice_success(self):
        """Lock ship details and audit after a successful IRN post."""
        self.ensure_one()
        self._rn_lock_ship_details_after_irn()
        response_ref = False
        try:
            response_ref = (self._get_l10n_in_edi_response_json() or {}).get('Irn')
        except Exception:
            response_ref = False
        self.env['rn.gst.api.audit'].log_api({
            'company_id': self.company_id.id,
            'gstin': self.company_id.vat,
            'document_model': 'account.move',
            'document_res_id': self.id,
            'document_name': self.name,
            'api_type': 'einvoice_generate',
            'api_environment': self.company_id.rn_gst_api_environment or 'sandbox',
            'success': True,
            'response_reference': response_ref,
        })
