# -*- coding: utf-8 -*-
import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nInEwaybill(models.Model):
    _name = 'l10n.in.ewaybill'
    _inherit = ['l10n.in.ewaybill', 'armora.gst.ewaybill.mixin']

    def action_armora_open_close_ewaybill_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Close E-Way Bill'),
            'res_model': 'armora.gst.ewaybill.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'l10n.in.ewaybill',
                'default_res_id': self.id,
                'default_ewb_number': self.armora_ewb_number or self.name,
                'default_closure_date': self.armora_ewb_closure_date or False,
            },
        }

    def action_close_ewaybill(self):
        self.ensure_one()
        return self.action_armora_open_close_ewaybill_wizard()

    def _armora_post_closure_action_allowed(self):
        self.ensure_one()
        if self.armora_ewb_status != 'closed':
            return True
        return bool(self.company_id.armora_gst_post_closure_actions_allowed)

    def write(self, vals):
        # During stabilisation, do not hard-block vehicle/transporter updates after closure
        # unless company configuration disables post-closure actions.
        sensitive = {'vehicle_no', 'transporter_id', 'mode', 'distance'}
        if sensitive.intersection(vals):
            for rec in self:
                if rec.armora_ewb_status == 'closed' and not rec._armora_post_closure_action_allowed():
                    raise UserError(_(
                        'Post-closure E-Way Bill modifications are disabled in company settings.'
                    ))
        return super().write(vals)

    def _write_successfully_response(self, response_vals):
        res = super()._write_successfully_response(response_vals)
        for rec in self:
            if rec.state == 'cancel':
                # Also called after a successful cancellation.
                sync = {'armora_ewb_status': 'cancelled'}
                message = _('E-Way Bill cancelled (Armora tracking updated).')
            else:
                sync = {
                    'armora_ewb_number': response_vals.get('name') or rec.name,
                    'armora_ewb_irn': (
                        rec.account_move_id and rec.account_move_id._get_l10n_in_edi_response_json().get('Irn')
                    ) or False,
                    'armora_ewb_status': 'active',
                    'armora_ewb_closure_status': 'open',
                    'armora_ewb_generation_date': response_vals.get('ewaybill_date') or rec.ewaybill_date,
                    'armora_ewb_validity_date': response_vals.get('ewaybill_expiry_date') or rec.ewaybill_expiry_date,
                    'armora_ewb_vehicle_no': rec.vehicle_no,
                    'armora_ewb_transporter_id': rec.transporter_id.id if rec.transporter_id else False,
                }
                message = _('E-Way Bill generated (Armora tracking updated).')
            # The portal already processed the request: never lose its response
            # because of an Armora tracking step.
            try:
                with self.env.cr.savepoint():
                    rec.write(sync)
                    # Invoice-side tracking (EWB generated from an invoice).
                    if rec.account_move_id:
                        rec.account_move_id.write(sync)
                        rec._armora_log_ewaybill_api(sync)
                    rec.message_post(body=message)
            except Exception:
                _logger.exception('Armora EWB tracking sync failed for %s', rec.display_name)
        return res

    def _armora_log_ewaybill_api(self, sync):
        self.ensure_one()
        move = self.account_move_id
        if self.state == 'cancel':
            api_type = 'ewaybill_cancel'
        elif self.is_sent_through_irn:
            api_type = 'ewaybill_by_irn'
        else:
            api_type = 'ewaybill_generate'
        self.env['armora.gst.api.audit'].log_api({
            'company_id': move.company_id.id,
            'gstin': move.company_id.vat,
            'document_model': 'account.move',
            'document_res_id': move.id,
            'document_name': move.name,
            'api_type': api_type,
            'api_environment': move.company_id.armora_gst_api_environment or 'sandbox',
            'success': True,
            'response_reference': sync.get('armora_ewb_number') or self.name,
        })
