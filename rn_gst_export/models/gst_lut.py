# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RnGstLut(models.Model):
    """Letter of Undertaking (form GST RFD-11) to export or supply to SEZ without paying IGST."""

    _name = 'rn.gst.lut'
    _description = 'GST Letter of Undertaking'
    _inherit = ['mail.thread']
    _order = 'valid_from desc, id desc'
    _rec_name = 'arn'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    gstin = fields.Char(string='GSTIN', required=True, index=True, default=lambda self: self.env.company.vat,
                        tracking=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    arn = fields.Char(string='LUT ARN', required=True, tracking=True,
                      help='Application Reference Number of the RFD-11 filed on the GST portal.')
    filed_date = fields.Date(tracking=True)
    valid_from = fields.Date(compute='_compute_validity', store=True, readonly=False, precompute=True, required=True,
                             tracking=True)
    valid_to = fields.Date(compute='_compute_validity', store=True, readonly=False, precompute=True, required=True,
                           tracking=True)
    active = fields.Boolean(default=True)
    note = fields.Text()
    invoice_ids = fields.One2many('account.move', 'rn_exp_lut_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    _rn_gst_lut_uniq = models.Constraint(
        'unique(company_id, gstin, financial_year)',
        "An LUT for this GSTIN and financial year is already recorded.",
    )

    @api.depends('financial_year')
    def _compute_validity(self):
        Period = self.env['rn.gst.filing.period']
        for lut in self:
            if not lut.financial_year:
                continue
            try:
                start = Period.fy_start_year(lut.financial_year)
            except ValidationError:
                continue
            lut.valid_from = fields.Date.to_date('%s-04-01' % start)
            lut.valid_to = fields.Date.to_date('%s-03-31' % (start + 1))

    @api.constrains('valid_from', 'valid_to')
    def _check_dates(self):
        for lut in self:
            if lut.valid_to < lut.valid_from:
                raise ValidationError(_('LUT end date must be after its start date.'))

    def _compute_invoice_count(self):
        counts = dict(self.env['account.move']._read_group(
            [('rn_exp_lut_id', 'in', self.ids)], ['rn_exp_lut_id'], ['__count']))
        for lut in self:
            lut.invoice_count = counts.get(lut, 0)

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices under LUT %s', self.arn),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('rn_exp_lut_id', '=', self.id)],
            'context': {'create': False},
        }

    @api.model_create_multi
    def create(self, vals_list):
        luts = super().create(vals_list)
        luts._rn_relink_invoices()
        return luts

    def write(self, vals):
        res = super().write(vals)
        if {'gstin', 'valid_from', 'valid_to', 'active', 'company_id'} & set(vals):
            self._rn_relink_invoices()
        return res

    def _rn_relink_invoices(self):
        """Recompute the LUT link of export invoices of the LUT's companies."""
        moves = self.env['account.move'].search([
            ('company_id', 'in', self.company_id.ids),
            ('rn_exp_kind', '!=', False),
        ])
        moves._rn_exp_recompute()
