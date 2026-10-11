# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_gst_validation_status = fields.Selection([
        ('pending', 'Pending'),
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ], default='pending', copy=False, index=True)
    rn_gst_validation_score = fields.Integer(string='GST Score', copy=False)
    rn_gst_validated_at = fields.Datetime(copy=False)
    rn_gst_issue_ids = fields.One2many(
        'rn.gst.invoice.issue',
        'move_id',
        string='GST Issues',
        copy=False,
    )
    rn_gst_error_count = fields.Integer(compute='_compute_rn_gst_issue_counts', store=True)
    rn_gst_warning_count = fields.Integer(compute='_compute_rn_gst_issue_counts', store=True)

    @api.depends('rn_gst_issue_ids', 'rn_gst_issue_ids.severity')
    def _compute_rn_gst_issue_counts(self):
        for move in self:
            move.rn_gst_error_count = len(move.rn_gst_issue_ids.filtered(lambda i: i.severity == 'error'))
            move.rn_gst_warning_count = len(move.rn_gst_issue_ids.filtered(lambda i: i.severity == 'warning'))

    def action_rn_gst_validate(self):
        for move in self:
            self.env['rn.gst.invoice.validator'].validate_move(move, persist=True)
        return True

    def action_rn_gst_view_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GST Issues'),
            'res_model': 'rn.gst.invoice.issue',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.id)],
            'context': {'default_move_id': self.id},
        }

    def _rn_gst_should_validate_on_post(self):
        self.ensure_one()
        if self.country_code != 'IN' or not self.is_invoice(include_receipts=True):
            return False
        company = self.company_id
        if self.is_sale_document(include_receipts=True):
            return bool(company.rn_gst_validate_sales)
        if self.is_purchase_document(include_receipts=True):
            return bool(company.rn_gst_validate_purchases)
        return False

    def _post(self, soft=True):
        to_check = self.filtered(lambda m: m._rn_gst_should_validate_on_post())
        for move in to_check:
            blocking = self.env['rn.gst.invoice.validator'].blocking_errors(move)
            if blocking and move.company_id.rn_gst_block_post_on_error:
                if self.env.context.get('rn_gst_force_post') and self.env.user.has_group(
                    'rn_gst_invoice_validator.group_rn_gst_validator_manager'
                ):
                    move.message_post(body=_(
                        'Posted with Armora GST override despite %s blocking error(s).'
                    ) % len(blocking))
                else:
                    details = '\n'.join('- %s' % i['message'] for i in blocking[:8])
                    more = ''
                    if len(blocking) > 8:
                        more = _('\n… and %s more.') % (len(blocking) - 8)
                    raise UserError(_(
                        'GST validation failed for %(move)s (score %(score)s/100).\n\n'
                        '%(details)s%(more)s\n\n'
                        'Fix the issues on the GST Validation tab, then post again.'
                    ) % {
                        'move': move.display_name,
                        'score': move.rn_gst_validation_score,
                        'details': details,
                        'more': more,
                    })
        return super()._post(soft=soft)

    def action_rn_gst_force_post(self):
        if not self.env.user.has_group('rn_gst_invoice_validator.group_rn_gst_validator_manager'):
            raise AccessError(_('Only GST Validator Managers can force-post with GST errors.'))
        return self.with_context(rn_gst_force_post=True).action_post()
