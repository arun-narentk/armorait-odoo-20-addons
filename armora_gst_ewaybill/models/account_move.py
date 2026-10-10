# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields, models, _
from odoo.exceptions import UserError


def _parse_gst_datetime(value):
    if not value:
        return False
    if hasattr(value, 'strftime'):
        return fields.Datetime.to_datetime(value)
    text = str(value)
    for fmt in (
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %I:%M:%S %p',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ):
        try:
            return fields.Datetime.to_datetime(datetime.strptime(text, fmt))
        except Exception:
            continue
    return False


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'armora.gst.ewaybill.mixin']

    def action_armora_open_close_ewaybill_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Close E-Way Bill'),
            'res_model': 'armora.gst.ewaybill.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'account.move',
                'default_res_id': self.id,
                'default_ewb_number': self.armora_ewb_number,
                'default_closure_date': self.armora_ewb_closure_date or False,
            },
        }

    def action_close_ewaybill(self):
        """API/service entry; UI should use the confirmation wizard."""
        self.ensure_one()
        return self.action_armora_open_close_ewaybill_wizard()

    def _armora_sync_ewb_from_response(self, data):
        self.ensure_one()
        vals = {}
        ewb_no = data.get('ewayBillNo') or data.get('EwbNo') or data.get('ewbNo')
        if ewb_no:
            vals['armora_ewb_number'] = str(ewb_no)
        if data.get('Irn') or data.get('irn'):
            vals['armora_ewb_irn'] = data.get('Irn') or data.get('irn')
        gen = data.get('ewayBillDate') or data.get('EwbDt')
        if gen:
            vals['armora_ewb_generation_date'] = _parse_gst_datetime(gen)
        valid = data.get('validUpto') or data.get('EwbValidTill')
        if valid:
            vals['armora_ewb_validity_date'] = _parse_gst_datetime(valid)
        vals['armora_ewb_status'] = 'active'
        vals['armora_ewb_closure_status'] = 'open'
        ewaybill = self.l10n_in_ewaybill_ids.filtered(lambda ewb: ewb.state == 'generated')[:1]
        if ewaybill.vehicle_no:
            vals['armora_ewb_vehicle_no'] = ewaybill.vehicle_no
        if ewaybill.transporter_id:
            vals['armora_ewb_transporter_id'] = ewaybill.transporter_id.id
        if vals:
            self.write(vals)

    def _armora_post_closure_action_allowed(self):
        self.ensure_one()
        if self.armora_ewb_status != 'closed':
            return True
        return bool(self.company_id.armora_gst_post_closure_actions_allowed)

    def write(self, vals):
        # Mirror l10n.in.ewaybill post-closure guard for invoice-side EWB fields.
        sensitive = {
            'armora_ewb_vehicle_no',
            'armora_ewb_transporter_id',
        }
        if sensitive.intersection(vals):
            for move in self:
                if move.armora_ewb_status == 'closed' and not move._armora_post_closure_action_allowed():
                    raise UserError(_(
                        'Post-closure E-Way Bill modifications are disabled in company settings.'
                    ))
        return super().write(vals)
