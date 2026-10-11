# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RnGstRegistration(models.Model):
    _inherit = 'rn.gst.registration'

    is_default = fields.Boolean(
        string='Default for Company',
        help='Used for invoices and bills whose journal has no GST registration.',
    )
    journal_ids = fields.One2many('account.journal', 'rn_gst_registration_id', string='Journals')
    journal_count = fields.Integer(compute='_compute_document_counts')
    invoice_count = fields.Integer(compute='_compute_document_counts')
    bill_count = fields.Integer(compute='_compute_document_counts')
    mismatch_count = fields.Integer(string='Tax Type Warnings', compute='_compute_document_counts')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda r: r.is_default and r.active)._rn_fill_missing_documents()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default') or vals.get('active'):
            self.filtered(lambda r: r.is_default and r.active)._rn_fill_missing_documents()
        return res

    def _rn_fill_missing_documents(self, journals=None):
        """Give this registration to the invoices and bills that have none yet: those of
        ``journals``, or for a default registration those of journals without their own
        registration. Documents that already have a registration are never changed."""
        for rec in self:
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('rn_gst_registration_id', '=', False),
                ('move_type', '!=', 'entry'),
            ]
            if journals is not None:
                domain.append(('journal_id', 'in', journals.ids))
            else:
                domain.append(('journal_id.rn_gst_registration_id', '=', False))
            moves = self.env['account.move'].search(domain)
            if moves:
                moves.write({'rn_gst_registration_id': rec.id})

    @api.constrains('is_default', 'company_id', 'active')
    def _check_single_default(self):
        for rec in self.filtered(lambda r: r.is_default and r.active):
            if self.search_count([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('is_default', '=', True),
            ]):
                raise ValidationError(_('Company %s already has a default GST registration.', rec.company_id.name))

    def _compute_document_counts(self):
        Move = self.env['account.move']
        counts = {
            (registration.id, kind): count
            for registration, kind, count in Move._read_group(
                [('rn_gst_registration_id', 'in', self.ids), ('state', '!=', 'cancel')],
                ['rn_gst_registration_id', 'move_type'], ['__count'],
            )
        }
        mismatches = dict(Move._read_group(
            [('rn_gst_registration_id', 'in', self.ids), ('rn_gst_tax_mismatch', '=', True), ('state', '!=', 'cancel')],
            ['rn_gst_registration_id'], ['__count'],
        ))
        for rec in self:
            rec.journal_count = len(rec.journal_ids)
            rec.invoice_count = sum(counts.get((rec.id, t), 0) for t in ('out_invoice', 'out_refund', 'out_receipt'))
            rec.bill_count = sum(counts.get((rec.id, t), 0) for t in ('in_invoice', 'in_refund', 'in_receipt'))
            rec.mismatch_count = mismatches.get(rec, 0)

    def _rn_moves_action(self, name, domain):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(self.env.ref('account.view_invoice_tree').id, 'list'), (False, 'form')],
            'domain': [('rn_gst_registration_id', '=', self.id)] + domain,
            'context': {'create': False},
        }

    def action_view_invoices(self):
        return self._rn_moves_action(_('Invoices'), [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt'))])

    def action_view_bills(self):
        return self._rn_moves_action(_('Bills'), [('move_type', 'in', ('in_invoice', 'in_refund', 'in_receipt'))])

    def action_view_mismatches(self):
        return self._rn_moves_action(_('Tax Type Warnings'), [('rn_gst_tax_mismatch', '=', True)])

    def action_view_journals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journals'),
            'res_model': 'account.journal',
            'view_mode': 'list,form',
            'domain': [('rn_gst_registration_id', '=', self.id)],
            'context': {'default_rn_gst_registration_id': self.id, 'default_company_id': self.company_id.id},
        }

    @api.model
    def _rn_default_for_company(self, company):
        """Default registration of a company: the one marked default, else the active
        registration with the company's own GSTIN, else the only active one."""
        registrations = self.search([('company_id', '=', company.id)])
        return (
            registrations.filtered('is_default')[:1]
            or registrations.filtered(lambda r: company.vat and r.gstin == company.vat)[:1]
            or (registrations if len(registrations) == 1 else self.browse())
        )
