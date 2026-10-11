# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

OPEN_STATES = ('new', 'in_progress', 'waiting')
SEVERITY_MAP = {'error': 'error', 'warning': 'warning', 'review': 'warning'}


class RnGstException(models.Model):
    """A GST problem to follow up: found by an Armora GST app or added by hand.

    Apps push problems with ``_rn_sync_findings``. Each problem has a stable
    ``fingerprint`` so that a second scan updates the same record instead of
    adding a new one, and problems that are no longer found are closed.
    """

    _name = 'rn.gst.exception'
    _description = 'GST Exception'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_deadline, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    title = fields.Char(required=True, tracking=True)
    message = fields.Text(string='Details')
    hint = fields.Text(string='How to Fix')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    gstin = fields.Char(string='GSTIN', index=True)
    source = fields.Selection([
        ('manual', 'Added by hand'),
        ('invoice_validator', 'Invoice Validator'),
        ('gstr2b', 'GSTR-2B Reconciliation'),
        ('filing', 'GSTR-1 Filing'),
        ('other', 'Other App'),
    ], required=True, default='manual', index=True, readonly=True)
    category = fields.Selection([
        ('sales', 'Sales Invoice'),
        ('purchase', 'Vendor Bill'),
        ('return', 'Return Filing'),
        ('master', 'Master Data'),
        ('other', 'Other'),
    ], required=True, default='other', index=True)
    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], required=True, default='warning', index=True, tracking=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'High')], default='0')
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ], required=True, default='new', index=True, tracking=True, copy=False)
    is_open = fields.Boolean(compute='_compute_is_open', search='_search_is_open')
    user_id = fields.Many2one('res.users', string='Owner', index=True, tracking=True,
                              domain="[('share', '=', False)]")
    date_deadline = fields.Date(string='Deadline', tracking=True)
    is_overdue = fields.Boolean(compute='_compute_is_overdue', search='_search_is_overdue')
    res_model = fields.Char(string='Document Model', readonly=True)
    res_id = fields.Many2oneReference(string='Document ID', model_field='res_model', readonly=True)
    move_id = fields.Many2one('account.move', string='Invoice / Bill', index=True, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='set null')
    fingerprint = fields.Char(readonly=True, copy=False, index=True,
                              help='Stable key of the problem in its app. Empty for problems added by hand.')
    first_seen = fields.Datetime(readonly=True, default=fields.Datetime.now, copy=False)
    last_seen = fields.Datetime(readonly=True, default=fields.Datetime.now, copy=False)
    seen_count = fields.Integer(string='Times Found', readonly=True, default=1, copy=False)
    auto_resolved = fields.Boolean(readonly=True, copy=False,
                                   help='Closed by the scan because the app no longer finds the problem.')
    resolved_by_id = fields.Many2one('res.users', string='Closed By', readonly=True, copy=False)
    resolved_date = fields.Datetime(string='Closed On', readonly=True, copy=False)
    resolution_note = fields.Text(tracking=True)

    _rn_gst_exception_fingerprint_uniq = models.UniqueIndex(
        '(company_id, fingerprint) WHERE fingerprint IS NOT NULL',
        "This problem is already in the GST exception inbox.",
    )

    @api.depends('state')
    def _compute_is_open(self):
        for rec in self:
            rec.is_open = rec.state in OPEN_STATES

    def _search_is_open(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        is_open = value if operator == '=' else not value
        return [('state', 'in' if is_open else 'not in', OPEN_STATES)]

    @api.depends('date_deadline', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.state in OPEN_STATES and rec.date_deadline and rec.date_deadline < today)

    def _search_is_overdue(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('state', 'in', OPEN_STATES) & Domain('date_deadline', '<', fields.Date.context_today(self))
        return domain if (operator == '=') == value else ~domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.exception') or _('New')
        records = super().create(vals_list)
        records.filtered('user_id')._rn_schedule_owner_activity()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('user_id'):
            self.filtered(lambda r: r.state in OPEN_STATES)._rn_schedule_owner_activity()
        return res

    def _rn_schedule_owner_activity(self):
        for rec in self:
            rec.activity_unlink(['mail.mail_activity_data_todo'])
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=rec.date_deadline or fields.Date.context_today(rec),
                summary=rec.title,
                user_id=rec.user_id.id,
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id})
        self.filtered(lambda r: r.state == 'new').write({'state': 'in_progress'})
        return True

    def action_start(self):
        self.write({'state': 'in_progress'})
        return True

    def action_wait(self):
        self.write({'state': 'waiting'})
        return True

    def action_resolve(self):
        self._rn_close('resolved')
        return True

    def action_ignore(self):
        missing = self.filtered(lambda r: not r.resolution_note)
        if missing:
            raise UserError(_('Write a resolution note before ignoring %s.', ', '.join(missing.mapped('name'))))
        self._rn_close('ignored')
        return True

    def action_reopen(self):
        self.write({
            'state': 'new',
            'auto_resolved': False,
            'resolved_by_id': False,
            'resolved_date': False,
        })
        self.filtered('user_id')._rn_schedule_owner_activity()
        return True

    def _rn_close(self, state, auto=False):
        self.write({
            'state': state,
            'auto_resolved': auto,
            'resolved_by_id': False if auto else self.env.user.id,
            'resolved_date': fields.Datetime.now(),
        })
        self.activity_unlink(['mail.mail_activity_data_todo'])

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_('This problem is not linked to a document.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Posting API for the GST apps
    # ------------------------------------------------------------------

    @api.model
    def _rn_sync_findings(self, source, findings, company_ids, fingerprint_prefix=None):
        """Create or refresh the problems an app finds, and close the ones it no longer finds.

        :param source: value of the ``source`` field
        :param findings: list of dicts with at least ``fingerprint``, ``company_id`` and ``title``;
            other keys are field values (``message``, ``hint``, ``severity``, ``move_id``, ...)
        :param company_ids: companies that were scanned; only their open problems of this
            source can be closed
        :param fingerprint_prefix: when set, only problems whose fingerprint starts with it
            are updated or closed (for apps that share a source)
        :return: dict with the number of ``created``, ``updated``, ``reopened`` and ``closed`` problems
        """
        now = fields.Datetime.now()
        by_key = {}
        for finding in findings:
            by_key[(finding['company_id'], finding['fingerprint'])] = finding
        domain = [
            ('source', '=', source),
            ('company_id', 'in', company_ids),
            ('fingerprint', '!=', False),
        ]
        if fingerprint_prefix:
            domain.append(('fingerprint', '=like', fingerprint_prefix + '%'))
        existing = self.with_context(active_test=False).search(domain)
        stats = dict.fromkeys(('created', 'updated', 'reopened', 'closed'), 0)
        seen = set()
        for rec in existing:
            key = (rec.company_id.id, rec.fingerprint)
            finding = by_key.get(key)
            if not finding:
                if rec.state in OPEN_STATES:
                    rec._rn_close('resolved', auto=True)
                    rec.message_post(body=_('Closed: the app no longer finds this problem.'))
                    stats['closed'] += 1
                continue
            seen.add(key)
            vals = {k: v for k, v in finding.items() if k not in ('fingerprint', 'company_id')}
            vals.update({'last_seen': now, 'seen_count': rec.seen_count + 1})
            if rec.state == 'resolved':
                vals.update({'state': 'new', 'auto_resolved': False, 'resolved_by_id': False, 'resolved_date': False})
                stats['reopened'] += 1
            else:
                stats['updated'] += 1
            rec.write(vals)
            if vals.get('state') == 'new':
                rec.message_post(body=_('Opened again: the app still finds this problem.'))
                if rec.user_id:
                    rec._rn_schedule_owner_activity()
        new_vals = [
            dict(finding, source=source, first_seen=now, last_seen=now)
            for key, finding in by_key.items() if key not in seen
        ]
        if new_vals:
            self.create(new_vals)
            stats['created'] = len(new_vals)
        return stats

    @api.model
    def _rn_collectors(self):
        """Map of source to method that returns its current findings. Apps may extend it."""
        return {
            'invoice_validator': self._rn_collect_invoice_validator,
            'gstr2b': self._rn_collect_gstr2b,
            'filing': self._rn_collect_filing,
        }

    @api.model
    def _rn_collect_invoice_validator(self, companies):
        if 'rn.gst.invoice.issue' not in self.env:
            return None
        issues = self.env['rn.gst.invoice.issue'].sudo().search([
            ('company_id', 'in', companies.ids),
            ('severity', 'in', tuple(SEVERITY_MAP)),
            ('move_id.state', '!=', 'cancel'),
        ])
        error_types = dict(issues._fields['error_type']._description_selection(self.env))
        findings = {}
        for issue in issues:
            move = issue.move_id
            fingerprint = 'inv:%s:%s:%s' % (move.id, issue.error_type, issue.move_line_id.id or 0)
            if fingerprint in findings:
                findings[fingerprint]['message'] += '\n' + issue.message
                continue
            findings[fingerprint] = {
                'fingerprint': fingerprint,
                'company_id': move.company_id.id,
                'gstin': move.company_id.vat or False,
                'title': '%s: %s' % (move.name or _('Draft'), error_types.get(issue.error_type, issue.error_type)),
                'message': issue.message,
                'hint': issue.hint or False,
                'severity': SEVERITY_MAP[issue.severity],
                'category': 'purchase' if move.is_purchase_document(include_receipts=True) else 'sales',
                'move_id': move.id,
                'partner_id': move.partner_id.id or False,
                'res_model': 'account.move',
                'res_id': move.id,
            }
        return list(findings.values())

    @api.model
    def _rn_collect_gstr2b(self, companies):
        if 'rn.gst.gstr2b.line' not in self.env:
            return None
        labels = {
            'mismatch': _('Amounts differ from GSTR-2B'),
            'missing_in_odoo': _('In GSTR-2B but no bill in Odoo'),
            'missing_in_2b': _('Bill not in GSTR-2B'),
        }
        lines = self.env['rn.gst.gstr2b.line'].sudo().search([
            ('company_id', 'in', companies.ids),
            ('match_state', 'in', tuple(labels)),
            ('reconciliation_id.state', 'not in', ('cancelled', 'closed')),
        ])
        findings = []
        for line in lines:
            recon = line.reconciliation_id
            # Lines are created again on each import; key on the document, not the line id.
            fingerprint = '2b:%s:%s:%s:%s' % (
                recon.gstin, recon.financial_year, recon.return_period,
                line.move_id.id or '%s/%s' % (line.vendor_gstin, line.invoice_number),
            )
            findings.append({
                'fingerprint': fingerprint,
                'company_id': line.company_id.id,
                'gstin': recon.gstin,
                'title': '%s %s: %s' % (line.vendor_name or line.partner_id.name or line.vendor_gstin or '',
                                        line.invoice_number or '', labels[line.match_state]),
                'message': line.mismatch_detail or False,
                'severity': 'error' if line.match_state == 'missing_in_2b' else 'warning',
                'category': 'purchase',
                'move_id': line.move_id.id or False,
                'partner_id': line.partner_id.id or False,
                'res_model': 'rn.gst.gstr2b',
                'res_id': recon.id,
            })
        return findings

    @api.model
    def _rn_collect_filing(self, companies):
        if 'rn.gst.validation.result' not in self.env:
            return None
        results = self.env['rn.gst.validation.result'].sudo().search([
            ('company_id', 'in', companies.ids),
            ('severity', '=', 'error'),
            ('filing_id.state', 'not in', ('filed', 'cancelled')),
        ])
        error_types = dict(results._fields['error_type']._description_selection(self.env))
        findings = {}
        for result in results:
            filing = result.filing_id
            fingerprint = 'filing:%s:%s:%s' % (
                filing.id, result.error_type, result.move_id.id or result.partner_id.id or 0,
            )
            if fingerprint in findings:
                continue
            findings[fingerprint] = {
                'fingerprint': fingerprint,
                'company_id': filing.company_id.id,
                'gstin': filing.gstin or False,
                'title': '%s: %s' % (filing.display_name, error_types.get(result.error_type, result.error_type)),
                'message': result.message,
                'hint': result.hint or False,
                'severity': 'error',
                'category': 'return',
                'move_id': result.move_id.id or False,
                'partner_id': result.partner_id.id or False,
                'res_model': 'rn.gst.filing',
                'res_id': filing.id,
            }
        return list(findings.values())

    @api.model
    def _rn_collect_all(self, companies):
        totals = dict.fromkeys(('created', 'updated', 'reopened', 'closed'), 0)
        for source, collector in self._rn_collectors().items():
            findings = collector(companies)
            if findings is None:
                continue
            stats = self._rn_sync_findings(source, findings, companies.ids)
            for key, count in stats.items():
                totals[key] += count
        return totals

    def action_collect(self):
        """Button on the inbox: scan the companies selected in the company switcher.
        Called from the list header, so it runs on whatever records are selected (often none)."""
        totals = self._rn_collect_all(self.env.companies)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('GST exceptions refreshed'),
                'message': _(
                    '%(created)s new, %(updated)s still open, %(reopened)s opened again, %(closed)s closed.',
                    **totals,
                ),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    @api.model
    def _cron_collect(self):
        self._rn_collect_all(self.env['res.company'].search([]))
