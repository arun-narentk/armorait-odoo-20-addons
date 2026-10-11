# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

CANCEL_HOURS = 24
REPORT_DAYS = 30


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_einv_state = fields.Selection([
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('generated', 'IRN Generated'),
        ('cancelled', 'Cancelled'),
        ('cancel_needed', 'Cancel IRN'),
    ], string='E-Invoice', compute='_compute_rn_einv_state', store=True, index='btree_not_null',
        help='Cancel IRN: the invoice was cancelled in Odoo but its IRN is still live on the IRP.')
    rn_einv_irn = fields.Char(string='IRN No.', copy=False, readonly=True)
    rn_einv_ack_no = fields.Char(string='Ack No', copy=False, readonly=True)
    rn_einv_ack_date = fields.Datetime(string='Ack Date', copy=False, readonly=True)
    rn_einv_cancel_until = fields.Datetime(
        string='IRN Cancel Until', compute='_compute_rn_einv_deadlines', store=True,
        help='The IRP lets an IRN be cancelled within 24 hours of its acknowledgement.',
    )
    rn_einv_report_by = fields.Date(
        string='Report IRN By', compute='_compute_rn_einv_deadlines', store=True,
        help='30 days after the invoice date, for companies with the 30-day limit set.',
    )
    rn_einv_days_pending = fields.Integer(string='Days Without IRN', compute='_compute_rn_einv_live')
    rn_einv_cancel_open = fields.Boolean(
        string='Cancel Window Open', compute='_compute_rn_einv_live', search='_search_rn_einv_cancel_open',
    )
    rn_einv_report_late = fields.Boolean(
        string='Past 30 Days', compute='_compute_rn_einv_live', search='_search_rn_einv_report_late',
    )

    @api.depends('state', 'move_type', 'l10n_in_edi_status', 'l10n_in_edi_error')
    def _compute_rn_einv_state(self):
        for move in self:
            status = move.l10n_in_edi_status
            if move.state == 'cancel' and status == 'sent':
                move.rn_einv_state = 'cancel_needed'
            elif status == 'to_send':
                move.rn_einv_state = 'failed' if move.l10n_in_edi_error else 'pending'
            elif status == 'sent':
                move.rn_einv_state = 'generated'
            elif status == 'cancelled':
                move.rn_einv_state = 'cancelled'
            else:
                move.rn_einv_state = False

    @api.depends('rn_einv_ack_date', 'invoice_date', 'company_id.rn_einv_30_day_rule', 'rn_einv_state')
    def _compute_rn_einv_deadlines(self):
        for move in self:
            move.rn_einv_cancel_until = move.rn_einv_ack_date and move.rn_einv_ack_date + timedelta(hours=CANCEL_HOURS)
            move.rn_einv_report_by = (
                move.invoice_date + timedelta(days=REPORT_DAYS)
                if move.invoice_date and move.rn_einv_state and move.company_id.rn_einv_30_day_rule else False
            )

    @api.depends('rn_einv_state', 'invoice_date', 'rn_einv_cancel_until', 'rn_einv_report_by')
    def _compute_rn_einv_live(self):
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        for move in self:
            waiting = move.rn_einv_state in ('pending', 'failed')
            move.rn_einv_days_pending = (today - move.invoice_date).days if waiting and move.invoice_date else 0
            move.rn_einv_cancel_open = bool(
                move.rn_einv_state in ('generated', 'cancel_needed') and move.rn_einv_cancel_until
                and move.rn_einv_cancel_until > now
            )
            move.rn_einv_report_late = bool(waiting and move.rn_einv_report_by and move.rn_einv_report_by < today)

    def _search_rn_einv_cancel_open(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('rn_einv_state', 'in', ('generated', 'cancel_needed')) & Domain(
            'rn_einv_cancel_until', '>', fields.Datetime.now())
        return domain if (operator == '=') == value else ~domain

    def _search_rn_einv_report_late(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        domain = Domain('rn_einv_state', 'in', ('pending', 'failed')) & Domain(
            'rn_einv_report_by', '<', fields.Date.context_today(self))
        return domain if (operator == '=') == value else ~domain

    # ------------------------------------------------------------------
    # IRN details
    # ------------------------------------------------------------------

    def _rn_einv_store_ack(self):
        """Copy IRN, acknowledgement number and date from the IRP response kept by l10n_in_edi."""
        for move in self.filtered(lambda m: m.l10n_in_edi_status in ('sent', 'cancelled') and m.l10n_in_edi_attachment_id):
            try:
                data = move._get_l10n_in_edi_response_json() or {}
            except (ValueError, TypeError) as err:
                _logger.warning('Cannot read the e-invoice response of %s: %s', move.display_name, err)
                continue
            ack_date = False
            if data.get('AckDt'):
                try:
                    # IRP gives Indian time; Odoo keeps UTC.
                    ack_date = datetime.strptime(data['AckDt'], '%Y-%m-%d %H:%M:%S') - timedelta(hours=5, minutes=30)
                except ValueError:
                    ack_date = False
            move.write({
                'rn_einv_irn': data.get('Irn') or False,
                'rn_einv_ack_no': str(data['AckNo']) if data.get('AckNo') else False,
                'rn_einv_ack_date': ack_date,
            })

    def _l10n_in_edi_send_invoice(self):
        res = super()._l10n_in_edi_send_invoice()
        if self.l10n_in_edi_status == 'sent':
            self._rn_einv_store_ack()
        return res

    @api.model
    def _cron_rn_einv_fill_ack(self, limit=500):
        self.search([
            ('l10n_in_edi_status', 'in', ('sent', 'cancelled')),
            ('rn_einv_ack_date', '=', False),
        ], limit=limit)._rn_einv_store_ack()

    def action_rn_einv_send_again(self):
        """Send failed or pending e-invoices to the IRP again through l10n_in_edi."""
        moves = self.filtered(lambda m: m.rn_einv_state in ('pending', 'failed'))
        if not moves:
            raise UserError(_('Pick invoices that are pending or failed.'))
        failed = []
        for move in moves:
            result = move._l10n_in_edi_send_invoice()
            if result:
                failed.append('%s: %s' % (move.display_name, '; '.join(str(m) for m in result.get('messages', []))))
        message = _('%(ok)s of %(total)s sent.', ok=len(moves) - len(failed), total=len(moves))
        if failed:
            message += '\n' + '\n'.join(failed[:10])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('E-invoices sent again'),
                'message': message,
                'type': 'warning' if failed else 'success',
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
