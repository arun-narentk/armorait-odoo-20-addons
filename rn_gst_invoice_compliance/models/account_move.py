# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

READINESS = [
    ('not_checked', 'Not Checked'),
    ('blocked', 'Blocked'),
    ('review', 'Needs Review'),
    ('ready', 'Ready'),
    ('approved', 'Approved'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_gst_readiness = fields.Selection(
        READINESS, string='GST Readiness', compute='_compute_rn_gst_readiness', store=True,
        index='btree_not_null', tracking=True,
        help='Ready: no GST problem found. Needs Review: warnings to look at. Blocked: errors to fix '
             'before filing. Approved: a reviewer accepted the listed problems.',
    )
    rn_gst_readiness_reasons = fields.Text(
        string='Readiness Reasons', compute='_compute_rn_gst_readiness', store=True,
    )
    rn_gst_approved_reasons = fields.Text(copy=False, readonly=True,
                                          help='The problems the reviewer accepted.')
    rn_gst_reviewer_id = fields.Many2one('res.users', string='Reviewed By', copy=False, readonly=True)
    rn_gst_review_date = fields.Datetime(string='Reviewed On', copy=False, readonly=True)
    rn_gst_review_note = fields.Text(string='Review Note', copy=False, readonly=True)

    def _rn_readiness_depends(self):
        names = [
            'move_type', 'state', 'country_code', 'rn_gst_validation_status', 'rn_gst_error_count',
            'rn_gst_warning_count', 'rn_gst_approved_reasons',
        ]
        # Fields of other apps, used only when those apps are installed.
        names += [f for f in ('rn_cn_check_state', 'rn_gst_tax_mismatch', 'l10n_in_edi_status') if f in self._fields]
        return names

    @api.depends(lambda self: self._rn_readiness_depends())
    def _compute_rn_gst_readiness(self):
        for move in self:
            if move.country_code != 'IN' or not move.is_invoice(include_receipts=True) or move.state == 'cancel':
                move.rn_gst_readiness = False
                move.rn_gst_readiness_reasons = False
                continue
            blockers, reviews = move._rn_gst_readiness_findings()
            reasons = '\n'.join([_('Blocked: %s', b) for b in blockers] + [_('Review: %s', r) for r in reviews])
            move.rn_gst_readiness_reasons = reasons or False
            if reasons and move.rn_gst_approved_reasons == reasons:
                move.rn_gst_readiness = 'approved'
            elif blockers:
                move.rn_gst_readiness = 'blocked'
            elif move.rn_gst_validation_status == 'pending':
                move.rn_gst_readiness = 'not_checked'
            elif reviews:
                move.rn_gst_readiness = 'review'
            else:
                move.rn_gst_readiness = 'ready'

    def _rn_gst_readiness_findings(self):
        """(blockers, review points) as short sentences."""
        self.ensure_one()
        blockers, reviews = [], []
        status = self.rn_gst_validation_status
        if status == 'error':
            blockers.append(_('%s GST validation error(s)', self.rn_gst_error_count or 1))
        elif status == 'warning':
            reviews.append(_('%s GST validation warning(s)', self.rn_gst_warning_count or 1))
        if self._fields.get('rn_cn_check_state'):
            if self.rn_cn_check_state == 'error':
                blockers.append(_('credit note breaks a GST rule'))
            elif self.rn_cn_check_state == 'warning':
                reviews.append(_('credit note has GST warnings'))
        if self._fields.get('rn_gst_tax_mismatch') and self.rn_gst_tax_mismatch:
            blockers.append(_('IGST used where CGST/SGST is due, or the other way round'))
        if self._fields.get('l10n_in_edi_status') and self.state == 'posted':
            if self.l10n_in_edi_status == 'to_send':
                blockers.append(_('e-invoice IRN not generated'))
            elif self.l10n_in_edi_status == 'cancelled':
                blockers.append(_('e-invoice IRN cancelled but the invoice is still posted'))
        return blockers, reviews

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def _rn_gst_approve(self, note):
        user = self.env.user
        if not user.has_group('rn_gst_invoice_compliance.group_rn_gst_compliance_reviewer'):
            raise AccessError(_('Only GST compliance reviewers can approve invoices.'))
        blocked = self.filtered(lambda m: m.rn_gst_readiness == 'blocked')
        if blocked and not user.has_group('rn_gst_invoice_compliance.group_rn_gst_compliance_manager'):
            raise AccessError(_(
                'Only a GST compliance manager can approve blocked invoices: %s',
                ', '.join(blocked.mapped('display_name')),
            ))
        if blocked and not note:
            raise UserError(_('Write why the blocking problems are accepted.'))
        to_approve = self.filtered(lambda m: m.rn_gst_readiness in ('blocked', 'review', 'not_checked'))
        for move in to_approve:
            move.write({
                'rn_gst_approved_reasons': move.rn_gst_readiness_reasons,
                'rn_gst_reviewer_id': user.id,
                'rn_gst_review_date': fields.Datetime.now(),
                'rn_gst_review_note': note or False,
            })
            move.message_post(body=_(
                'GST readiness approved by %(user)s.\n%(reasons)s\nNote: %(note)s',
                user=user.name, reasons=move.rn_gst_readiness_reasons or '', note=note or '-',
            ))
        return to_approve

    def action_rn_gst_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve GST Readiness'),
            'res_model': 'rn.gst.compliance.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_ids': self.ids},
        }

    def action_rn_gst_reset_review(self):
        self.write({
            'rn_gst_approved_reasons': False,
            'rn_gst_reviewer_id': False,
            'rn_gst_review_date': False,
            'rn_gst_review_note': False,
        })
        return True

    def action_rn_gst_validate_selected(self):
        """List button: run the GST validator on the selected invoices."""
        moves = self.filtered(lambda m: m.is_invoice(include_receipts=True) and m.state != 'cancel')
        moves.action_rn_gst_validate()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('GST validation done'),
                'message': _('%s invoice(s) checked.', len(moves)),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
