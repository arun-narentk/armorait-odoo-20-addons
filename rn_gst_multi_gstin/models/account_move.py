# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Supplies that always carry IGST, whatever the states (IGST Act section 7(5) and 16).
IGST_TREATMENTS = ('overseas', 'special_economic_zone')


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_gst_registration_id = fields.Many2one(
        'rn.gst.registration',
        string='Our GSTIN',
        compute='_compute_rn_gst_registration_id',
        store=True,
        readonly=False,
        precompute=True,
        index='btree_not_null',
        check_company=True,
        tracking=True,
        help='GST registration this invoice or bill is issued or received under. '
             'Taken from the journal, else the default registration of the company.',
    )
    rn_gst_supply_type = fields.Selection(
        [('intra', 'Intra-state'), ('inter', 'Inter-state')],
        string='Supply Type',
        compute='_compute_rn_gst_supply',
        store=True,
        help='Intra-state supplies carry CGST and SGST, inter-state supplies carry IGST.',
    )
    rn_gst_tax_mismatch = fields.Boolean(
        string='Tax Type Warning',
        compute='_compute_rn_gst_supply',
        store=True,
    )
    rn_gst_tax_warning = fields.Char(compute='_compute_rn_gst_supply', store=True)

    @api.depends('journal_id', 'company_id')
    def _compute_rn_gst_registration_id(self):
        Registration = self.env['rn.gst.registration']
        defaults = {}
        for move in self:
            if not move.is_invoice(include_receipts=True):
                move.rn_gst_registration_id = False
                continue
            registration = move.journal_id.rn_gst_registration_id
            if not registration:
                company = move.company_id
                if company not in defaults:
                    defaults[company] = Registration._rn_default_for_company(company)
                registration = defaults[company]
            move.rn_gst_registration_id = registration

    def _rn_gst_our_state(self):
        self.ensure_one()
        return self.rn_gst_registration_id.state_id or self.company_id.state_id

    def _rn_gst_other_state(self):
        """State of the other party: the place of supply on sales, the supplier's state on purchases."""
        self.ensure_one()
        if self.is_sale_document(include_receipts=True):
            return self.l10n_in_state_id
        partner = self.partner_id.commercial_partner_id
        if partner.vat and partner.vat[:2].isdigit():
            state = self.env['res.country.state'].search([
                ('country_id.code', '=', 'IN'), ('l10n_in_tin', '=', partner.vat[:2]),
            ], limit=1)
            if state:
                return state
        return partner.state_id

    @api.depends(
        'rn_gst_registration_id', 'l10n_in_state_id', 'l10n_in_gst_treatment', 'partner_id',
        'invoice_line_ids.tax_ids', 'move_type',
    )
    def _compute_rn_gst_supply(self):
        for move in self:
            move.rn_gst_supply_type = False
            move.rn_gst_tax_mismatch = False
            move.rn_gst_tax_warning = False
            if move.country_code != 'IN' or not move.is_invoice(include_receipts=True):
                continue
            ours, other = move._rn_gst_our_state(), move._rn_gst_other_state()
            if not ours or (not other and move.l10n_in_gst_treatment not in IGST_TREATMENTS):
                continue
            inter = move.l10n_in_gst_treatment in IGST_TREATMENTS or ours != other
            move.rn_gst_supply_type = 'inter' if inter else 'intra'
            taxes = move.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
            tax_types = set(taxes.mapped('l10n_in_gst_tax_type'))
            gstin = move.rn_gst_registration_id.gstin or move.company_id.vat or ''
            if inter and tax_types & {'cgst', 'sgst'}:
                other_name = other.name or _('outside India')
                if move.is_sale_document(include_receipts=True):
                    supplier_state, recipient_state = ours.name, other_name
                else:
                    supplier_state, recipient_state = other_name, ours.name
                move.rn_gst_tax_mismatch = True
                move.rn_gst_tax_warning = _(
                    'Inter-state supply (%(supplier)s to %(recipient)s, our GSTIN %(gstin)s) should carry IGST, '
                    'but the lines use CGST/SGST.',
                    supplier=supplier_state, recipient=recipient_state, gstin=gstin,
                )
            elif not inter and 'igst' in tax_types:
                move.rn_gst_tax_mismatch = True
                move.rn_gst_tax_warning = _(
                    'Intra-state supply in %(state)s (our GSTIN %(gstin)s) should carry CGST and SGST, '
                    'but the lines use IGST.',
                    state=ours.name, gstin=gstin,
                )

    def _post(self, soft=True):
        for move in self.filtered('rn_gst_registration_id'):
            registration = move.rn_gst_registration_id
            doc_date = move.invoice_date or move.date or fields.Date.context_today(move)
            if not registration.active:
                raise UserError(_(
                    '%(move)s: GST registration %(reg)s is archived. Pick another registration or journal.',
                    move=move.display_name, reg=registration.display_name,
                ))
            if (registration.effective_from and doc_date < registration.effective_from) or (
                registration.effective_to and doc_date > registration.effective_to
            ):
                raise UserError(_(
                    '%(move)s is dated %(date)s, outside the effective dates of GST registration %(reg)s '
                    '(%(start)s to %(end)s).',
                    move=move.display_name, date=doc_date, reg=registration.display_name,
                    start=registration.effective_from or '...', end=registration.effective_to or '...',
                ))
        return super()._post(soft)
