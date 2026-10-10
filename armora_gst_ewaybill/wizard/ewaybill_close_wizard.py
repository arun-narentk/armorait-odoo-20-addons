# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ArmoraGstEwaybillCloseWizard(models.TransientModel):
    _name = 'armora.gst.ewaybill.close.wizard'
    _description = 'Close E-Way Bill Wizard'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    ewb_number = fields.Char(string='E-Way Bill Number', required=True)
    delivery_date = fields.Date(string='Delivery Date')
    closure_date = fields.Date(string='Closure Date', required=True, default=fields.Date.context_today)
    remarks = fields.Char(string='Remarks', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        return res

    def action_confirm_closure(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record.exists():
            raise UserError(_('Related document was not found.'))
        result = self.env['armora.gst.ewaybill.close.service'].action_close_ewaybill(
            record,
            ewb_number=self.ewb_number,
            closure_date=self.closure_date,
            remarks=self.remarks,
            delivery_date=self.delivery_date,
        )
        if not result.get('success'):
            if result.get('retryable'):
                raise UserError(_(
                    'Closure failed (%(code)s): %(msg)s\nYou can retry this request.',
                    code=result.get('error_code'),
                    msg=result.get('error'),
                ))
            raise UserError(_(
                'Closure failed (%(code)s): %(msg)s',
                code=result.get('error_code'),
                msg=result.get('error'),
            ))
        return {'type': 'ir.actions.act_window_close'}
