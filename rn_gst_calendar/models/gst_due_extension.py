# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RnGstDueExtension(models.Model):
    """A due date moved by a government notification, for all states or some of them."""

    _name = 'rn.gst.due.extension'
    _description = 'GST Due-Date Extension'
    _order = 'financial_year desc, return_period desc, id desc'

    return_type_id = fields.Many2one('rn.gst.return.type', required=True, ondelete='cascade', index=True)
    financial_year = fields.Char(required=True, help='e.g. 2025-26')
    return_period = fields.Char(required=True, help='Month 01-12, quarter Q1-Q4, or FY for an annual return.')
    state_ids = fields.Many2many(
        'res.country.state', string='States', domain="[('country_id.code', '=', 'IN')]",
        help='Leave empty when the extension applies to all states.',
    )
    new_due_date = fields.Date(required=True)
    reference = fields.Char(string='Notification', help='e.g. Notification No. 12/2025-Central Tax')
    note = fields.Text()

    @api.depends('return_type_id', 'financial_year', 'return_period', 'new_due_date')
    def _compute_display_name(self):
        for ext in self:
            ext.display_name = '%s %s/%s: %s' % (
                ext.return_type_id.name, ext.financial_year, ext.return_period, ext.new_due_date,
            )

    @api.model_create_multi
    def create(self, vals_list):
        extensions = super().create(vals_list)
        extensions._rn_update_obligations()
        return extensions

    def write(self, vals):
        before = self._rn_obligations()
        res = super().write(vals)
        (before | self._rn_obligations())._rn_apply_due_dates()
        return res

    def unlink(self):
        obligations = self._rn_obligations()
        res = super().unlink()
        obligations._rn_apply_due_dates()
        return res

    def _rn_obligations(self):
        Obligation = self.env['rn.gst.obligation']
        for ext in self:
            Obligation |= Obligation.search([
                ('return_type_id', '=', ext.return_type_id.id),
                ('financial_year', '=', ext.financial_year),
                ('return_period', '=', ext.return_period),
            ])
        return Obligation

    def _rn_update_obligations(self):
        self._rn_obligations()._rn_apply_due_dates()

    def _rn_covers(self, registration):
        self.ensure_one()
        return not self.state_ids or registration.state_id in self.state_ids
