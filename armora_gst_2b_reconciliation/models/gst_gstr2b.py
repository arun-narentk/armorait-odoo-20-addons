# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ArmoraGstGstr2b(models.Model):
    _name = 'armora.gst.gstr2b'
    _description = 'GSTR-2A / GSTR-2B Reconciliation'
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
    statement_type = fields.Selection([
        ('gstr2b', 'GSTR-2B'),
        ('gstr2a', 'GSTR-2A'),
    ], string='Statement', required=True, default='gstr2b', tracking=True, index=True,
        help='GSTR-2B is the fixed monthly ITC statement. GSTR-2A changes as suppliers file '
             'and also shows whether each supplier filed GSTR-1 and GSTR-3B.')
    gstin = fields.Char(required=True, tracking=True, index=True)
    financial_year = fields.Char(required=True, tracking=True)
    return_period = fields.Char(
        required=True,
        tracking=True,
        help='Month MM within the financial year (e.g. 04 for April).',
    )
    filing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], required=True, default='monthly', tracking=True)
    period_start = fields.Date(required=True, index=True, tracking=True)
    period_end = fields.Date(required=True, index=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('matched', 'Matched'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, index=True, copy=False)

    line_ids = fields.One2many('armora.gst.gstr2b.line', 'reconciliation_id', string='Lines')
    notes = fields.Text()

    # Dashboard totals
    amount_itc_total = fields.Monetary(
        compute='_compute_dashboard', store=True, currency_field='currency_id',
        string='Total ITC (2B)',
    )
    amount_matched = fields.Monetary(compute='_compute_dashboard', store=True, currency_field='currency_id')
    amount_mismatch = fields.Monetary(compute='_compute_dashboard', store=True, currency_field='currency_id')
    amount_missing_odoo = fields.Monetary(
        compute='_compute_dashboard', store=True, currency_field='currency_id',
        string='Missing in Odoo',
    )
    amount_missing_2b = fields.Monetary(
        compute='_compute_dashboard', store=True, currency_field='currency_id',
        string='Missing in 2B',
    )
    count_matched = fields.Integer(compute='_compute_dashboard', store=True)
    count_mismatch = fields.Integer(compute='_compute_dashboard', store=True)
    count_missing_odoo = fields.Integer(compute='_compute_dashboard', store=True)
    count_missing_2b = fields.Integer(compute='_compute_dashboard', store=True)
    count_ignored = fields.Integer(compute='_compute_dashboard', store=True)
    count_disputed = fields.Integer(compute='_compute_dashboard', store=True)
    line_count = fields.Integer(compute='_compute_dashboard', store=True)

    matched_at = fields.Datetime(copy=False)
    matched_by = fields.Many2one('res.users', copy=False)

    _armora_gst_gstr2b_period_uniq = models.Constraint(
        'unique(company_id, gstin, statement_type, financial_year, return_period)',
        "A reconciliation of this statement already exists for this company, GSTIN and period.",
    )

    @api.depends(
        'line_ids', 'line_ids.match_state', 'line_ids.source',
        'line_ids.taxable_value', 'line_ids.cgst_amount', 'line_ids.sgst_amount',
        'line_ids.igst_amount', 'line_ids.cess_amount',
    )
    def _compute_dashboard(self):
        for rec in self:
            lines = rec.line_ids
            rec.line_count = len(lines)

            def _itc(subset):
                return (
                    sum(subset.mapped('cgst_amount'))
                    + sum(subset.mapped('sgst_amount'))
                    + sum(subset.mapped('igst_amount'))
                    + sum(subset.mapped('cess_amount'))
                )

            gstr2b_lines = lines.filtered(lambda l: l.source == 'gstr2b')
            rec.amount_itc_total = _itc(gstr2b_lines)

            matched = lines.filtered(lambda l: l.match_state == 'matched')
            mismatch = lines.filtered(lambda l: l.match_state == 'mismatch')
            missing_odoo = lines.filtered(lambda l: l.match_state == 'missing_in_odoo')
            missing_2b = lines.filtered(lambda l: l.match_state == 'missing_in_2b')
            ignored = lines.filtered(lambda l: l.match_state == 'ignored')
            disputed = lines.filtered(lambda l: l.match_state == 'disputed')

            rec.count_matched = len(matched)
            rec.count_mismatch = len(mismatch)
            rec.count_missing_odoo = len(missing_odoo)
            rec.count_missing_2b = len(missing_2b)
            rec.count_ignored = len(ignored)
            rec.count_disputed = len(disputed)

            rec.amount_matched = _itc(matched)
            rec.amount_mismatch = _itc(mismatch)
            rec.amount_missing_odoo = _itc(missing_odoo)
            rec.amount_missing_2b = _itc(missing_2b)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.gstin = self.company_id.vat or ''

    @api.onchange('financial_year', 'return_period', 'filing_frequency')
    def _onchange_period(self):
        if self.financial_year and self.return_period and self.filing_frequency:
            try:
                start, end = self.env['armora.gst.period'].compute_period_dates(
                    self.financial_year, self.return_period, self.filing_frequency
                )
                self.period_start = start
                self.period_end = end
            except ValidationError:
                pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                code = 'armora.gst.gstr2a' if vals.get('statement_type') == 'gstr2a' else 'armora.gst.gstr2b'
                vals['name'] = self.env['ir.sequence'].next_by_code(code) or _('New')
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
            if not vals.get('gstin'):
                vals['gstin'] = company.vat or ''
            if vals.get('financial_year') and vals.get('return_period'):
                if not vals.get('period_start') or not vals.get('period_end'):
                    start, end = self.env['armora.gst.period'].compute_period_dates(
                        vals['financial_year'], vals['return_period'], vals.get('filing_frequency') or 'monthly',
                    )
                    vals['period_start'] = start
                    vals['period_end'] = end
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.state in ('closed', 'cancelled') and not self.env.su:
                protected = set(vals.keys()) - {
                    'message_follower_ids', 'activity_ids', 'message_ids', '__last_update', 'notes',
                }
                if protected:
                    raise UserError(_('Closed or cancelled reconciliations are read-only.'))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'closed' and not self.env.su:
                raise UserError(_('Closed reconciliations cannot be deleted.'))
        return super().unlink()

    def action_run_matching(self):
        self.ensure_one()
        if self.state in ('closed', 'cancelled'):
            raise UserError(_('This reconciliation is closed.'))
        if not self.line_ids.filtered(lambda l: l.source == 'gstr2b'):
            raise UserError(_('Import the %s file before running matching.', self._statement_label()))
        self.env['armora.gst.2b.matching'].match_reconciliation(self)
        self.write({
            'state': 'matched',
            'matched_at': fields.Datetime.now(),
            'matched_by': self.env.user.id,
        })
        return True

    def action_mark_closed(self):
        for rec in self:
            if not self.env.user.has_group('armora_gst_2b_reconciliation.group_armora_gst_2b_manager'):
                raise AccessError(_('Only GSTR-2B Managers can close reconciliations.'))
            if rec.state not in ('matched', 'imported'):
                raise UserError(_('Run matching before closing, or close from imported/matched state.'))
            rec.state = 'closed'
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state in ('closed', 'cancelled'):
                raise UserError(_('Closed or cancelled reconciliations cannot be reset.'))
            rec.line_ids.filtered(lambda l: l.source == 'odoo').unlink()
            rec.line_ids.write({
                'match_state': 'pending',
                'move_id': False,
                'mismatch_detail': False,
                'diff_taxable_value': 0.0,
                'diff_cgst': 0.0,
                'diff_sgst': 0.0,
                'diff_igst': 0.0,
                'diff_cess': 0.0,
            })
            rec.write({
                'state': 'draft' if not rec.line_ids else 'imported',
                'matched_at': False,
                'matched_by': False,
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'closed':
                raise UserError(_('Closed reconciliations cannot be cancelled.'))
            rec.state = 'cancelled'
        return True

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import %s', self._statement_label()),
            'res_model': 'armora.gst.2b.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reconciliation_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }

    def _statement_label(self):
        self.ensure_one()
        return dict(self._fields['statement_type']._description_selection(self.env)).get(self.statement_type)

    def _action_view_lines(self, match_state=None, name=None):
        self.ensure_one()
        domain = [('reconciliation_id', '=', self.id)]
        if match_state:
            domain.append(('match_state', '=', match_state))
        return {
            'type': 'ir.actions.act_window',
            'name': name or _('2B Lines'),
            'res_model': 'armora.gst.gstr2b.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_reconciliation_id': self.id},
        }

    def action_view_lines(self):
        return self._action_view_lines()

    def action_view_matched(self):
        return self._action_view_lines('matched', _('Matched'))

    def action_view_mismatch(self):
        return self._action_view_lines('mismatch', _('Mismatch'))

    def action_view_missing_odoo(self):
        return self._action_view_lines('missing_in_odoo', _('Missing in Odoo'))

    def action_view_missing_2b(self):
        return self._action_view_lines('missing_in_2b', _('Missing in 2B'))
