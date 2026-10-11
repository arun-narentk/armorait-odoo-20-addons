# -*- coding: utf-8 -*-
from odoo import models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_rn_open_close_ewaybill_wizard(self):
        self.ensure_one()
        ewb = self.env['l10n.in.ewaybill'].search([('picking_id', '=', self.id)], limit=1)
        if not ewb:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No E-Way Bill'),
                    'message': _('No E-Way Bill is linked to this transfer.'),
                    'type': 'warning',
                },
            }
        return ewb.action_rn_open_close_ewaybill_wizard()
