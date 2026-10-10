# -*- coding: utf-8 -*-
"""Logical GST rate definition mapped to existing ``account.tax`` records.

Does not compute invoice tax. Odoo ``account.tax`` remains the calculation engine.
Component percentages are configuration metadata for validation and change control.
"""

from decimal import Decimal

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.armora_gst_base.services import rates as rate_service


class ArmoraGstRate(models.Model):
    _name = 'armora.gst.rate'
    _description = 'Armora GST Rate Definition'
    _order = 'company_id, code, effective_from desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        required=True,
        help='Display label for this rate definition (for example GST 18%).',
    )
    code = fields.Char(
        required=True,
        index=True,
        help='Stable technical code for this rate family. Versions share the same code '
             'with different effective dates.',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    gst_registration_id = fields.Many2one(
        'armora.gst.registration',
        string='GST Registration',
        check_company=True,
        index=True,
        help='Optional. Leave empty for company-wide rate definitions.',
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )

    # --- Classification / applicability (metadata only) ---
    tax_category = fields.Selection(
        selection=[
            ('general', 'General'),
            ('goods', 'Goods'),
            ('services', 'Services'),
        ],
        default='general',
        required=True,
        index=True,
        help='Optional applicability hint. Does not replace product tax_scope on account.tax.',
    )
    type_applicability = fields.Selection(
        selection=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('both', 'Sale and Purchase'),
        ],
        default='both',
        required=True,
        index=True,
    )
    hsn_sac_code = fields.Char(
        string='HSN/SAC',
        index=True,
        help='Optional association to an HSN/SAC code. Classification validation belongs '
             'to armora_gst_hsn_validator. Empty means a general rate band.',
    )

    # --- Component rates (configuration metadata; not used to post tax) ---
    # Odoo models State/UT tax as SGST tags; do not invent a separate UTGST field.
    igst_rate = fields.Float(
        string='IGST %',
        digits=(16, 4),
        help='Integrated GST percentage for inter-state supplies.',
    )
    cgst_rate = fields.Float(
        string='CGST %',
        digits=(16, 4),
        help='Central GST percentage for intra-state supplies.',
    )
    sgst_rate = fields.Float(
        string='SGST/UTGST %',
        digits=(16, 4),
        help='State/UT GST percentage. Odoo Indian localization uses SGST tags for both.',
    )
    cess_rate = fields.Float(
        string='Cess %',
        digits=(16, 4),
        help='Optional ad valorem cess percentage when applicable.',
    )
    total_gst_rate = fields.Float(
        string='Total GST %',
        digits=(16, 4),
        compute='_compute_total_gst_rate',
        store=True,
        help='IGST when set, otherwise CGST + SGST. Cess is separate.',
    )

    # --- Effective dating ---
    effective_from = fields.Date(
        required=True,
        index=True,
        default=fields.Date.context_today,
    )
    effective_to = fields.Date(
        index=True,
        help='Inclusive end date. Leave empty for open-ended rates.',
    )

    # --- Linked Odoo taxes (existing chart taxes; do not auto-create) ---
    tax_sale_intra_id = fields.Many2one(
        'account.tax',
        string='Sale Intra-State Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale'), "
               "('country_id.code', '=', 'IN')]",
        help='Usually the GST group tax (CGST+SGST children), e.g. 18% GST sale.',
    )
    tax_sale_inter_id = fields.Many2one(
        'account.tax',
        string='Sale Inter-State Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale'), "
               "('country_id.code', '=', 'IN')]",
        help='Usually the IGST sale tax at the same band.',
    )
    tax_purchase_intra_id = fields.Many2one(
        'account.tax',
        string='Purchase Intra-State Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), "
               "('country_id.code', '=', 'IN')]",
    )
    tax_purchase_inter_id = fields.Many2one(
        'account.tax',
        string='Purchase Inter-State Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), "
               "('country_id.code', '=', 'IN')]",
    )
    tax_cess_sale_id = fields.Many2one(
        'account.tax',
        string='Sale Cess Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale'), "
               "('country_id.code', '=', 'IN')]",
    )
    tax_cess_purchase_id = fields.Many2one(
        'account.tax',
        string='Purchase Cess Tax',
        check_company=True,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), "
               "('country_id.code', '=', 'IN')]",
    )

    source_reference = fields.Char(
        string='Source / Reference',
        help='Internal reference for this configuration (for example change ticket). '
             'Do not paste fabricated government notification numbers.',
    )
    note = fields.Text()

    _armora_gst_rate_code_company_from_uniq = models.Constraint(
        'unique(company_id, code, effective_from)',
        "A rate version with this code and effective-from date already exists for the company.",
    )

    @api.depends('igst_rate', 'cgst_rate', 'sgst_rate')
    def _compute_total_gst_rate(self):
        for rec in self:
            igst = rate_service.normalize_gst_rate(rec.igst_rate or 0)
            if igst:
                rec.total_gst_rate = float(igst)
            else:
                total = rate_service.normalize_gst_rate(rec.cgst_rate or 0) + rate_service.normalize_gst_rate(
                    rec.sgst_rate or 0
                )
                rec.total_gst_rate = float(total)

    @api.onchange('igst_rate')
    def _onchange_igst_rate(self):
        """Suggest equal CGST/SGST split when IGST is evenly divisible."""
        for rec in self:
            if not rec.igst_rate:
                continue
            try:
                half, _half = rate_service.split_igst_rate_to_cgst_sgst(rec.igst_rate)
            except Exception:
                continue
            rec.cgst_rate = float(half)
            rec.sgst_rate = float(half)

    @api.onchange('gst_registration_id')
    def _onchange_gst_registration_id(self):
        if self.gst_registration_id:
            self.company_id = self.gst_registration_id.company_id

    def _rate_as_decimal(self, value):
        return rate_service.normalize_gst_rate(value or 0)

    def _is_historical_locked(self):
        """True when the rate version must not be rewritten in place."""
        self.ensure_one()
        if self.state in ('expired', 'cancelled'):
            return True
        if self.effective_to and self.effective_to < fields.Date.context_today(self):
            return True
        return False

    def _periods_overlap(self, from_a, to_a, from_b, to_b):
        """Inclusive date ranges; empty end date means open-ended."""
        end_a = to_a or fields.Date.to_date('9999-12-31')
        end_b = to_b or fields.Date.to_date('9999-12-31')
        return from_a <= end_b and from_b <= end_a

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for rec in self:
            if rec.effective_from and rec.effective_to and rec.effective_to < rec.effective_from:
                raise ValidationError(_(
                    'Effective To (%(to)s) cannot be before Effective From (%(frm)s) on rate %(name)s.',
                    to=rec.effective_to,
                    frm=rec.effective_from,
                    name=rec.display_name,
                ))

    @api.constrains('igst_rate', 'cgst_rate', 'sgst_rate', 'cess_rate')
    def _check_component_rates(self):
        for rec in self:
            for label, value in (
                (_('IGST'), rec.igst_rate),
                (_('CGST'), rec.cgst_rate),
                (_('SGST'), rec.sgst_rate),
                (_('Cess'), rec.cess_rate),
            ):
                amount = self._rate_as_decimal(value)
                if amount < Decimal('0'):
                    raise ValidationError(_('%s rate cannot be negative.', label))
            igst = self._rate_as_decimal(rec.igst_rate)
            cgst = self._rate_as_decimal(rec.cgst_rate)
            sgst = self._rate_as_decimal(rec.sgst_rate)
            if igst and (cgst or sgst) and (cgst + sgst) != igst:
                raise ValidationError(_(
                    'On rate %(name)s, CGST (%(cgst)s) + SGST (%(sgst)s) must equal IGST (%(igst)s).',
                    name=rec.display_name,
                    cgst=cgst,
                    sgst=sgst,
                    igst=igst,
                ))
            if (cgst or sgst) and cgst != sgst:
                raise ValidationError(_(
                    'On rate %(name)s, CGST (%(cgst)s) and SGST (%(sgst)s) must be equal for a standard GST band.',
                    name=rec.display_name,
                    cgst=cgst,
                    sgst=sgst,
                ))

    @api.constrains(
        'company_id', 'code', 'effective_from', 'effective_to', 'state', 'active',
        'hsn_sac_code', 'tax_category', 'type_applicability', 'gst_registration_id',
    )
    def _check_overlapping_versions(self):
        """Prevent overlapping active versions for the same applicability context."""
        for rec in self:
            # Only enforce overlap among currently active rates.
            if not rec.active or rec.state != 'active':
                continue
            domain = [
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('code', '=', rec.code),
                ('active', '=', True),
                ('state', '=', 'active'),
                ('tax_category', '=', rec.tax_category),
                ('type_applicability', '=', rec.type_applicability),
                ('hsn_sac_code', '=', rec.hsn_sac_code or False),
                ('gst_registration_id', '=', rec.gst_registration_id.id or False),
            ]
            rivals = self.search(domain)
            for other in rivals:
                if self._periods_overlap(
                    rec.effective_from, rec.effective_to,
                    other.effective_from, other.effective_to,
                ):
                    raise ValidationError(_(
                        'Active rate "%(name)s" overlaps "%(other)s" for code %(code)s '
                        'in the same company/applicability context. Close the previous '
                        'version (set Effective To) before activating a new one.',
                        name=rec.display_name,
                        other=other.display_name,
                        code=rec.code,
                    ))

    @api.constrains(
        'tax_sale_intra_id', 'tax_sale_inter_id',
        'tax_purchase_intra_id', 'tax_purchase_inter_id',
        'tax_cess_sale_id', 'tax_cess_purchase_id', 'company_id',
    )
    def _check_mapped_tax_company(self):
        tax_fields = (
            'tax_sale_intra_id', 'tax_sale_inter_id',
            'tax_purchase_intra_id', 'tax_purchase_inter_id',
            'tax_cess_sale_id', 'tax_cess_purchase_id',
        )
        for rec in self:
            for fname in tax_fields:
                tax = rec[fname]
                if tax and tax.company_id != rec.company_id:
                    raise ValidationError(_(
                        'Mapped tax "%(tax)s" belongs to another company than rate %(name)s.',
                        tax=tax.display_name,
                        name=rec.display_name,
                    ))

    def write(self, vals):
        locked_fields = {
            'igst_rate', 'cgst_rate', 'sgst_rate', 'cess_rate',
            'effective_from', 'code', 'hsn_sac_code', 'tax_category',
            'type_applicability',
            'tax_sale_intra_id', 'tax_sale_inter_id',
            'tax_purchase_intra_id', 'tax_purchase_inter_id',
            'tax_cess_sale_id', 'tax_cess_purchase_id',
        }
        if locked_fields.intersection(vals):
            for rec in self:
                if rec._is_historical_locked():
                    raise ValidationError(_(
                        'Historical rate "%(name)s" cannot be rewritten in place. '
                        'Create a new version with a new Effective From date instead.',
                        name=rec.display_name,
                    ))
        return super().write(vals)

    def action_set_active(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise ValidationError(_('Cancelled rates cannot be activated.'))
            rec.state = 'active'
        return True

    def action_set_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            vals = {'state': 'expired'}
            if not rec.effective_to or rec.effective_to > today:
                vals['effective_to'] = today
            # Expire without going through historical lock on effective_to when still active.
            super(ArmoraGstRate, rec).write(vals)
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled', 'active': False})
        return True

    @api.model
    def find_overlapping_rates(self, company, code, effective_from, effective_to=False,
                               tax_category='general', type_applicability='both',
                               hsn_sac_code=False, gst_registration=False, exclude_id=False):
        """Return active rates overlapping the given period for the applicability key."""
        domain = [
            ('company_id', '=', company.id),
            ('code', '=', code),
            ('active', '=', True),
            ('state', '=', 'active'),
            ('tax_category', '=', tax_category),
            ('type_applicability', '=', type_applicability),
            ('hsn_sac_code', '=', hsn_sac_code or False),
            ('gst_registration_id', '=', gst_registration.id if gst_registration else False),
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        rivals = self.search(domain)
        return rivals.filtered(
            lambda r: self._periods_overlap(
                effective_from, effective_to, r.effective_from, r.effective_to,
            )
        )

    @api.model
    def get_rate_for_date(self, company, code, on_date=None, **kwargs):
        """Return the active rate version for ``code`` on ``on_date`` (Prompt 5 hook)."""
        on_date = on_date or fields.Date.context_today(self)
        domain = [
            ('company_id', '=', company.id),
            ('code', '=', code),
            ('active', '=', True),
            ('state', '=', 'active'),
            ('effective_from', '<=', on_date),
            '|',
            ('effective_to', '=', False),
            ('effective_to', '>=', on_date),
        ]
        if 'tax_category' in kwargs:
            domain.append(('tax_category', '=', kwargs['tax_category']))
        if 'type_applicability' in kwargs:
            domain.append(('type_applicability', '=', kwargs['type_applicability']))
        if 'hsn_sac_code' in kwargs:
            domain.append(('hsn_sac_code', '=', kwargs['hsn_sac_code'] or False))
        if 'gst_registration' in kwargs:
            reg = kwargs['gst_registration']
            domain.append(('gst_registration_id', '=', reg.id if reg else False))
        return self.search(domain, order='effective_from desc, id desc', limit=1)

    @api.depends('name', 'code', 'effective_from')
    def _compute_display_name(self):
        for rec in self:
            label = '%s [%s]' % (rec.name or '', rec.code or '')
            if rec.effective_from:
                label = '%s (%s)' % (label, rec.effective_from)
            rec.display_name = label
