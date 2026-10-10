# -*- coding: utf-8 -*-
from odoo import api, models

from ..services import gstin as gstin_service


class ArmoraGstGstinValidator(models.AbstractModel):
    """Structural GSTIN validation without external portal APIs.

    Pure logic lives in ``services.gstin``. This model adds optional Odoo
    state-master cross-checks. External GSTIN status verification belongs
    in a dedicated verification module.
    """

    _name = 'armora.gst.gstin.validator'
    _description = 'Armora GSTIN Validator'

    @api.model
    def normalize(self, value):
        return gstin_service.normalize_gstin(value)

    @api.model
    def _checksum_valid(self, gstin):
        return gstin_service.checksum_valid(gstin)

    @api.model
    def validate(self, value, company=None):
        """Return dict: status (valid/invalid/warning), message, normalized.

        ``company`` is accepted for API compatibility with callers; it is not
        used to invent or override GSTIN values.
        """
        del company  # explicit: do not guess from company
        result = gstin_service.validate_gstin(value)
        payload = {
            'status': result['status'],
            'message': result['message'],
            'normalized': result.get('normalized', ''),
        }
        if 'state_code' in result:
            payload['state_code'] = result['state_code']
            payload['pan'] = result['pan']
        if result['status'] != 'valid':
            return payload

        state_code = result['state_code']
        tin_state = self.env['res.country.state'].search([
            ('country_id.code', '=', 'IN'),
            ('l10n_in_tin', '=', state_code),
        ], limit=1)
        # 96/97 are special GST codes; may exist as l10n_in synthetic states.
        if not tin_state and state_code not in ('96', '97'):
            payload['status'] = 'warning'
            payload['message'] = (
                'GSTIN state code %s is not found in Odoo Indian states.' % state_code
            )
        return payload
