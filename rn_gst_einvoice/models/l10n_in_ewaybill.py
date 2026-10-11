# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import models


class L10nInEwaybill(models.Model):
    _inherit = 'l10n.in.ewaybill'

    def _ewaybill_generate_irn_json(self):
        json_payload = super()._ewaybill_generate_irn_json()
        move = self.account_move_id
        if move and move.company_id.rn_gst_enable_einvoice:
            json_payload = move._rn_enrich_ewaybill_by_irn_payload(json_payload)
        return json_payload

    def _generate_ewaybill_by_irn(self):
        move = self.account_move_id
        if message := move._rn_einvoice_validation_error():
            self._write_error(Markup('<br/>').join(message.split('\n')))
            return False
        return super()._generate_ewaybill_by_irn()
