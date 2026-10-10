# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ArmoraGstFiling(models.Model):
    _name = 'armora.gst.filing'
    _description = 'GST Filing Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_end desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    gst_registration_id = fields.Many2one(
        'armora.gst.registration',
        string='GST Registration',
        index=True,
        tracking=True,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help='Armora GST registration (multi-GSTIN). GSTIN is taken from this record when set.',
    )
    gstin = fields.Char(required=True, tracking=True, index=True)
    financial_year = fields.Char(required=True, tracking=True, help='e.g. 2025-26')
    return_period = fields.Char(
        required=True,
        tracking=True,
        help='Month MM or quarter Q1-Q4 within the financial year.',
    )
    filing_type = fields.Selection([
        ('gstr1', 'GSTR-1'),
        ('gstr1a', 'GSTR-1A'),
        ('gstr3b', 'GSTR-3B'),
        ('gstr9', 'GSTR-9'),
    ], required=True, default='gstr1', tracking=True, index=True)
    filing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], required=True, default='monthly', tracking=True)
    state_id = fields.Many2one('res.country.state', string='Company State', tracking=True)
    period_start = fields.Date(required=True, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)

    line_ids = fields.One2many('armora.gst.filing.line', 'filing_id', string='GST Lines')
    validation_result_ids = fields.One2many('armora.gst.validation.result', 'filing_id', string='Validation Results')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('data_loaded', 'Data Loaded'),
        ('validated', 'Validated'),
        ('generated', 'Generated'),
        ('submitted', 'Submitted'),
        ('filed', 'Filed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, index=True, copy=False)

    validation_status = fields.Selection([
        ('pending', 'Pending'),
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], default='pending', tracking=True, copy=False)
    validation_error_count = fields.Integer(default=0, copy=False)
    validation_warning_count = fields.Integer(default=0, copy=False)

    generated_file = fields.Binary(
        string='GST Upload File',
        attachment=True,
        copy=False,
        help='GSTR-1/IFF Excel workbook populated from the official GSTN Returns Offline Tool '
             'template. Import it into the Offline Tool; that tool generates the JSON uploaded '
             'to the GST Portal (this file is not uploaded directly to the portal).',
    )
    generated_filename = fields.Char(copy=False)
    generated_at = fields.Datetime(copy=False)
    generated_by = fields.Many2one('res.users', copy=False)

    template_id = fields.Many2one(
        'armora.gst.excel.template',
        string='Offline Tool Template',
        tracking=True,
        help='Official GSTN Returns Offline Tool Excel template uploaded by an administrator. '
             'Templates can change when GSTN updates the utility; select the version that matches '
             'the Offline Tool you use.',
    )
    template_version = fields.Char(copy=False)

    notes = fields.Text()

    # Summary / dashboard
    document_count = fields.Integer(compute='_compute_summary', store=True)
    line_count = fields.Integer(compute='_compute_summary', store=True)
    count_b2b = fields.Integer(compute='_compute_summary', store=True)
    count_b2cl = fields.Integer(compute='_compute_summary', store=True)
    count_b2cs = fields.Integer(compute='_compute_summary', store=True)
    count_export = fields.Integer(compute='_compute_summary', store=True)
    count_credit_note = fields.Integer(compute='_compute_summary', store=True)
    count_debit_note = fields.Integer(compute='_compute_summary', store=True)
    count_nil = fields.Integer(compute='_compute_summary', store=True)
    count_hsn = fields.Integer(compute='_compute_summary', store=True)

    amount_taxable = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_cgst = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_sgst = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_igst = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_cess = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_total_tax = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')
    amount_invoice = fields.Monetary(compute='_compute_summary', store=True, currency_field='currency_id')

    # Reconciliation (filled by validation service)
    recon_taxable_value = fields.Monetary(currency_field='currency_id', copy=False)
    recon_cgst = fields.Monetary(currency_field='currency_id', copy=False)
    recon_sgst = fields.Monetary(currency_field='currency_id', copy=False)
    recon_igst = fields.Monetary(currency_field='currency_id', copy=False)
    recon_cess = fields.Monetary(currency_field='currency_id', copy=False)
    recon_total_tax = fields.Monetary(currency_field='currency_id', copy=False)
    recon_invoice_value = fields.Monetary(currency_field='currency_id', copy=False)
    diff_taxable_value = fields.Monetary(currency_field='currency_id', copy=False)
    diff_cgst = fields.Monetary(currency_field='currency_id', copy=False)
    diff_sgst = fields.Monetary(currency_field='currency_id', copy=False)
    diff_igst = fields.Monetary(currency_field='currency_id', copy=False)
    diff_cess = fields.Monetary(currency_field='currency_id', copy=False)
    diff_total_tax = fields.Monetary(currency_field='currency_id', copy=False)
    diff_invoice_value = fields.Monetary(currency_field='currency_id', copy=False)

    is_readonly_state = fields.Boolean(compute='_compute_is_readonly_state')
    is_snapshot_locked = fields.Boolean(compute='_compute_is_readonly_state')

    _armora_gst_filing_period_uniq = models.Constraint(
        'unique(company_id, gstin, filing_type, financial_year, return_period)',
        "A filing already exists for this company, GSTIN, type and period.",
    )

    @api.depends('state')
    def _compute_is_readonly_state(self):
        for rec in self:
            rec.is_readonly_state = rec.state in ('submitted', 'filed', 'cancelled')
            # Snapshot is immutable once data has been loaded; regenerate explicitly.
            rec.is_snapshot_locked = rec.state != 'draft'

    @api.constrains('gst_registration_id', 'company_id', 'gstin')
    def _check_gst_registration_consistency(self):
        for rec in self:
            registration = rec.gst_registration_id
            if not registration:
                continue
            if registration.company_id != rec.company_id:
                raise ValidationError(_(
                    'GST registration %(reg)s belongs to company %(reg_company)s, '
                    'not filing company %(company)s.',
                    reg=registration.display_name,
                    reg_company=registration.company_id.display_name,
                    company=rec.company_id.display_name,
                ))
            if rec.gstin and registration.gstin and rec.gstin.upper() != registration.gstin.upper():
                raise ValidationError(_(
                    'Filing GSTIN %(gstin)s does not match registration GSTIN %(reg_gstin)s.',
                    gstin=rec.gstin,
                    reg_gstin=registration.gstin,
                ))

    @api.depends(
        'line_ids', 'line_ids.gst_table', 'line_ids.document_type',
        'line_ids.taxable_value', 'line_ids.cgst_amount', 'line_ids.sgst_amount',
        'line_ids.igst_amount', 'line_ids.cess_amount', 'line_ids.total_tax',
        'line_ids.invoice_value', 'line_ids.move_id', 'line_ids.hsn_code',
    )
    def _compute_summary(self):
        for rec in self:
            lines = rec.line_ids
            moves = lines.mapped('move_id')
            rec.line_count = len(lines)
            rec.document_count = len(moves) if moves else len(set(lines.mapped('invoice_number')))
            rec.count_b2b = len(lines.filtered(lambda l: l.gst_table == 'b2b').mapped('move_id'))
            rec.count_b2cl = len(lines.filtered(lambda l: l.gst_table == 'b2cl').mapped('move_id'))
            rec.count_b2cs = len(lines.filtered(lambda l: l.gst_table == 'b2cs'))
            rec.count_export = len(lines.filtered(lambda l: l.gst_table == 'exp').mapped('move_id'))
            rec.count_credit_note = len(lines.filtered(lambda l: l.document_type == 'credit_note').mapped('move_id'))
            rec.count_debit_note = len(lines.filtered(lambda l: l.document_type == 'debit_note').mapped('move_id'))
            rec.count_nil = len(lines.filtered(lambda l: l.gst_table == 'nil'))
            rec.count_hsn = len(set(filter(None, lines.mapped('hsn_code'))))
            rec.amount_taxable = sum(lines.mapped('taxable_value'))
            rec.amount_cgst = sum(lines.mapped('cgst_amount'))
            rec.amount_sgst = sum(lines.mapped('sgst_amount'))
            rec.amount_igst = sum(lines.mapped('igst_amount'))
            rec.amount_cess = sum(lines.mapped('cess_amount'))
            rec.amount_total_tax = sum(lines.mapped('total_tax'))
            if moves:
                rec.amount_invoice = sum(abs(m.amount_total_signed) for m in moves)
            else:
                seen = {}
                for line in lines:
                    if line.invoice_number not in seen:
                        seen[line.invoice_number] = line.invoice_value or 0.0
                rec.amount_invoice = sum(seen.values())

    def _compute_summary_from_lines(self):
        self._compute_summary()

    @api.model
    def compute_period_dates(self, financial_year, return_period, filing_frequency):
        return self.env['armora.gst.period'].compute_period_dates(
            financial_year, return_period, filing_frequency
        )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            if self.gst_registration_id and self.gst_registration_id.company_id != self.company_id:
                self.gst_registration_id = False
            if not self.gst_registration_id:
                self.gstin = self.company_id.vat or ''
                self.state_id = self.company_id.state_id

    @api.onchange('gst_registration_id')
    def _onchange_gst_registration_id(self):
        if self.gst_registration_id:
            self.company_id = self.gst_registration_id.company_id
            self.gstin = self.gst_registration_id.gstin or ''
            self.state_id = self.gst_registration_id.state_id

    @api.onchange('financial_year', 'return_period', 'filing_frequency')
    def _onchange_period(self):
        if self.financial_year and self.return_period and self.filing_frequency:
            try:
                start, end = self.compute_period_dates(
                    self.financial_year, self.return_period, self.filing_frequency
                )
                self.period_start = start
                self.period_end = end
            except ValidationError:
                pass

    @api.model_create_multi
    def create(self, vals_list):
        Registration = self.env['armora.gst.registration']
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('armora.gst.filing') or _('New')
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
            registration = False
            if vals.get('gst_registration_id'):
                registration = Registration.browse(vals['gst_registration_id'])
                vals['company_id'] = registration.company_id.id
                company = registration.company_id
                if not vals.get('gstin'):
                    vals['gstin'] = registration.gstin or ''
                if not vals.get('state_id'):
                    vals['state_id'] = registration.state_id.id
            if not vals.get('gstin'):
                vals['gstin'] = company.vat or ''
            if not vals.get('state_id'):
                vals['state_id'] = company.state_id.id
            if vals.get('financial_year') and vals.get('return_period') and vals.get('filing_frequency'):
                if not vals.get('period_start') or not vals.get('period_end'):
                    start, end = self.compute_period_dates(
                        vals['financial_year'], vals['return_period'], vals['filing_frequency']
                    )
                    vals['period_start'] = start
                    vals['period_end'] = end
        return super().create(vals_list)

    def _raise_readonly(self, message=None):
        raise UserError(message or _('This GST filing cannot be modified in its current state.'))

    def write(self, vals):
        vals = dict(vals)
        if vals.get('gst_registration_id'):
            registration = self.env['armora.gst.registration'].browse(vals['gst_registration_id'])
            vals.setdefault('company_id', registration.company_id.id)
            vals.setdefault('gstin', registration.gstin)
            vals.setdefault('state_id', registration.state_id.id)
        protected = set(vals.keys()) - {
            'message_follower_ids', 'activity_ids', 'message_ids', '__last_update',
        }
        for rec in self:
            if rec.state in ('filed', 'cancelled') and protected:
                # Allow admin notes? Still block for filed/cancelled.
                if not self.env.su:
                    raise UserError(_('Filed or cancelled GST filings are read-only.'))
            if rec.state == 'submitted':
                allowed_submitted = {
                    'state', 'notes', 'generated_file', 'generated_filename',
                    'generated_at', 'generated_by',
                }
                extra = protected - allowed_submitted
                if extra and not self.env.su:
                    raise UserError(_(
                        'Submitted filings cannot alter snapshot or validation fields. '
                        'Reset to draft (manager) to regenerate.'
                    ))
                if (
                    'state' in vals
                    and vals['state'] in ('filed', 'cancelled', 'draft')
                    and not self.env.su
                    and not self.env.user.has_group(
                        'armora_gst_filing.group_armora_gst_filing_manager'
                    )
                ):
                    raise UserError(_(
                        'Submitted filings can only be marked filed/cancelled by managers.'
                    ))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state in ('generated', 'submitted', 'filed'):
                if not self.env.user.has_group('armora_gst_filing.group_armora_gst_filing_administrator'):
                    raise AccessError(_('Only GST Filing Administrators can delete generated/submitted/filed returns.'))
            if rec.state == 'filed' and not self.env.su:
                raise UserError(_('Filed returns cannot be deleted.'))
        return super().unlink()

    def action_load_data(self):
        self.ensure_one()
        if self.state in ('submitted', 'filed', 'cancelled'):
            self._raise_readonly()
        self.env['armora.gst.data.extractor'].extract_to_filing(self, regenerate=bool(self.line_ids))
        return True

    def action_regenerate_snapshot(self):
        self.ensure_one()
        if not self.env.user.has_group('armora_gst_filing.group_armora_gst_filing_manager'):
            raise AccessError(_('Only GST Filing Managers can regenerate snapshots.'))
        if self.state in ('submitted', 'filed', 'cancelled'):
            self._raise_readonly()
        if self.state not in ('draft', 'data_loaded', 'validated', 'generated'):
            self._raise_readonly()
        self.env['armora.gst.data.extractor'].extract_to_filing(self, regenerate=True)
        return True

    def action_validate(self):
        self.ensure_one()
        if self.state in ('submitted', 'filed', 'cancelled'):
            self._raise_readonly()
        if not self.line_ids:
            raise UserError(_('Load GST data before validating.'))
        self.env['armora.gst.filing.validation'].validate_filing(self)
        return True

    def action_generate_excel(self):
        self.ensure_one()
        if self.validation_status == 'pending':
            self.action_validate()
        self.env['armora.gst.excel.generator'].generate(self)
        return True

    def action_download_excel(self):
        self.ensure_one()
        if not self.generated_file:
            raise UserError(_(
                'No GST upload file is available. '
                'Use Generate GST Upload File first.'
            ))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=armora.gst.filing&id=%s&field=generated_file&filename_field=generated_filename&download=true' % self.id,
            'target': 'self',
        }

    def action_mark_submitted(self):
        for rec in self:
            if rec.state != 'generated':
                raise UserError(_('Only generated filings can be marked as submitted.'))
            if not self.env.user.has_group('armora_gst_filing.group_armora_gst_filing_manager'):
                raise AccessError(_('Only GST Filing Managers can mark filings as submitted.'))
            rec.state = 'submitted'
        return True

    def action_mark_filed(self):
        for rec in self:
            if rec.state not in ('generated', 'submitted'):
                raise UserError(_('Only generated/submitted filings can be marked as filed.'))
            if not self.env.user.has_group('armora_gst_filing.group_armora_gst_filing_manager'):
                raise AccessError(_('Only GST Filing Managers can mark filings as filed.'))
            rec.state = 'filed'
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state in ('filed', 'cancelled'):
                raise UserError(_('Filed or cancelled filings cannot be reset.'))
            if rec.state == 'submitted' and not self.env.user.has_group(
                'armora_gst_filing.group_armora_gst_filing_manager'
            ):
                raise AccessError(_('Only managers can reset a submitted filing.'))
            rec.write({
                'state': 'draft',
                'validation_status': 'pending',
                'generated_file': False,
                'generated_filename': False,
                'generated_at': False,
                'generated_by': False,
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'filed':
                raise UserError(_('Filed filings cannot be cancelled. Contact an administrator if needed.'))
            rec.state = 'cancelled'
        return True

    def action_view_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GST Lines'),
            'res_model': 'armora.gst.filing.line',
            'view_mode': 'list,form',
            'domain': [('filing_id', '=', self.id)],
            'context': {'default_filing_id': self.id},
        }

    def action_view_validation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Validation'),
            'res_model': 'armora.gst.validation.result',
            'view_mode': 'list,form',
            'domain': [('filing_id', '=', self.id)],
            'context': {'default_filing_id': self.id, 'search_default_error': 1},
        }

    def action_fix_and_regenerate(self):
        """Open blocking issues so accountants can fix sources, then regenerate."""
        self.ensure_one()
        if self.state in ('submitted', 'filed', 'cancelled'):
            self._raise_readonly()
        if self.validation_status == 'pending':
            self.action_validate()
        action = self.action_view_validation()
        action['name'] = _('Fix GST Errors')
        action['context'] = {
            'default_filing_id': self.id,
            'search_default_error': 1,
            'armora_gst_after_fix_filing_id': self.id,
        }
        return action
