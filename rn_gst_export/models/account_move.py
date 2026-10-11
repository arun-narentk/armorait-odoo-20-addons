# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

EXPORT_TREATMENTS = ('overseas', 'special_economic_zone')
GOODS_EXPORT_MONTHS = 3     # Rule 96A(1)(a)
SERVICE_REALISE_MONTHS = 12  # Rule 96A(1)(b)
EXP_FIELDS = ('rn_exp_kind', 'rn_exp_has_goods', 'rn_exp_lut_id', 'rn_exp_check_state', 'rn_exp_check_messages',
              'rn_exp_refund_ready')


class AccountMove(models.Model):
    _inherit = 'account.move'

    rn_exp_kind = fields.Selection([
        ('lut', 'Under LUT (no IGST)'),
        ('igst', 'IGST paid'),
        ('mixed', 'Mixed'),
    ], string='Export Type', compute='_compute_rn_exp', store=True, index='btree_not_null')
    rn_exp_has_goods = fields.Boolean(string='Exports Goods', compute='_compute_rn_exp', store=True)
    rn_exp_lut_id = fields.Many2one('rn.gst.lut', string='LUT', compute='_compute_rn_exp', store=True,
                                    index='btree_not_null')
    rn_exp_check_state = fields.Selection([
        ('ok', 'No Issues'),
        ('warning', 'Warnings'),
        ('error', 'Errors'),
    ], string='Export Check', compute='_compute_rn_exp', store=True, index='btree_not_null')
    rn_exp_check_messages = fields.Text(string='Export Issues', compute='_compute_rn_exp', store=True)
    rn_exp_refund_ready = fields.Boolean(
        string='IGST Refund Ready', compute='_compute_rn_exp', store=True,
        help='IGST-paid goods export with shipping bill number, date and port: the refund can flow from '
             'GSTR-1 table 6A and GSTR-3B to ICEGATE.',
    )
    rn_exp_brc_number = fields.Char(string='e-BRC / FIRC No.', tracking=True, copy=False,
                                    help='Bank realisation certificate or foreign inward remittance number.')
    rn_exp_brc_date = fields.Date(string='e-BRC / FIRC Date', tracking=True, copy=False)
    rn_exp_realised_amount = fields.Monetary(string='Realised', compute='_compute_rn_exp_realisation',
                                             currency_field='currency_id')
    rn_exp_realised_date = fields.Date(string='Last Payment', compute='_compute_rn_exp_realisation')

    @api.depends('amount_residual', 'amount_total', 'payment_state')
    def _compute_rn_exp_realisation(self):
        for move in self:
            if not move.rn_exp_kind:
                move.rn_exp_realised_amount = 0.0
                move.rn_exp_realised_date = False
                continue
            move.rn_exp_realised_amount = move.amount_total - move.amount_residual
            payments = move._get_reconciled_payments()
            move.rn_exp_realised_date = max(payments.mapped('date'), default=False)

    def _rn_exp_recompute(self):
        for name in EXP_FIELDS:
            self.env.add_to_compute(self._fields[name], self)
        self.env.flush_all()

    @api.depends(
        'move_type', 'state', 'country_code', 'l10n_in_gst_treatment', 'invoice_date', 'company_id',
        'invoice_line_ids.tax_ids', 'invoice_line_ids.l10n_in_hsn_code', 'invoice_line_ids.product_id',
        'l10n_in_shipping_bill_number', 'l10n_in_shipping_bill_date', 'l10n_in_shipping_port_code_id',
        'payment_state', 'amount_residual',
    )
    def _compute_rn_exp(self):
        Lut = self.env['rn.gst.lut']
        today = fields.Date.context_today(self)
        for move in self:
            vals = dict.fromkeys(EXP_FIELDS, False)
            if (
                move.move_type not in ('out_invoice', 'out_refund') or move.country_code != 'IN'
                or move.l10n_in_gst_treatment not in EXPORT_TREATMENTS or move.state == 'cancel'
            ):
                move.update(vals)
                continue
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            taxes = lines.tax_ids.flatten_taxes_hierarchy()
            lut_taxes = taxes.filtered('l10n_in_is_lut')
            igst_taxes = taxes.filtered(lambda t: t.l10n_in_gst_tax_type == 'igst' and not t.l10n_in_is_lut)
            kind = 'mixed' if lut_taxes and igst_taxes else 'lut' if lut_taxes else 'igst' if igst_taxes else 'lut'
            goods = any(
                (line.l10n_in_hsn_code and not line.l10n_in_hsn_code.startswith('99'))
                or (not line.l10n_in_hsn_code and line.product_id.type != 'service')
                for line in lines
            )
            vals.update(rn_exp_kind=kind, rn_exp_has_goods=goods)
            errors, warnings = [], []
            invoice_date = move.invoice_date or today
            if kind in ('lut', 'mixed'):
                lut = Lut.search([
                    ('company_id', '=', move.company_id.id),
                    ('gstin', '=', move.company_id.vat),
                    ('valid_from', '<=', invoice_date),
                    ('valid_to', '>=', invoice_date),
                ], limit=1)
                vals['rn_exp_lut_id'] = lut.id
                if not lut:
                    errors.append(_(
                        'No LUT in force on %(date)s for GSTIN %(gstin)s. Record the LUT, or charge IGST.',
                        date=invoice_date, gstin=move.company_id.vat or '-',
                    ))
            if kind == 'mixed':
                errors.append(_('The invoice mixes LUT lines and IGST-paid lines. Use one way for the whole invoice.'))
            shipped_by = invoice_date + relativedelta(months=GOODS_EXPORT_MONTHS)
            is_export = move.l10n_in_gst_treatment == 'overseas'
            if is_export and goods:
                missing = [label for label, value in (
                    (_('shipping bill number'), move.l10n_in_shipping_bill_number),
                    (_('shipping bill date'), move.l10n_in_shipping_bill_date),
                    (_('port code'), move.l10n_in_shipping_port_code_id),
                ) if not value]
                if missing:
                    message = _('Missing %s.', ', '.join(missing))
                    if kind != 'igst' and today > shipped_by:
                        errors.append(_(
                            '%(missing)s Goods under LUT must be exported within 3 months (by %(date)s); '
                            'IGST with interest is now payable.', missing=message, date=shipped_by,
                        ))
                    else:
                        warnings.append(message)
                elif kind != 'igst' and move.l10n_in_shipping_bill_date > shipped_by:
                    errors.append(_(
                        'Shipping bill dated %(bill)s, more than 3 months after the invoice (limit %(date)s): '
                        'IGST with interest is payable on goods exported under LUT.',
                        bill=move.l10n_in_shipping_bill_date, date=shipped_by,
                    ))
            if is_export and not goods and kind != 'igst' and move.move_type == 'out_invoice':
                realise_by = invoice_date + relativedelta(months=SERVICE_REALISE_MONTHS)
                if move.payment_state not in ('paid', 'in_payment', 'reversed') and today > realise_by:
                    errors.append(_(
                        'Export of services under LUT not paid within one year (by %(date)s): IGST with '
                        'interest is payable.', date=realise_by,
                    ))
            vals['rn_exp_refund_ready'] = bool(
                is_export and goods and kind == 'igst' and move.l10n_in_shipping_bill_number
                and move.l10n_in_shipping_bill_date and move.l10n_in_shipping_port_code_id
            )
            vals['rn_exp_check_state'] = 'error' if errors else 'warning' if warnings else 'ok'
            vals['rn_exp_check_messages'] = '\n'.join(
                [_('Error: %s', e) for e in errors] + [_('Warning: %s', w) for w in warnings]
            ) or False
            move.update(vals)

    @api.model
    def _cron_rn_exp_recheck(self):
        """The 3-month and 1-year limits pass with time: check open export invoices again every day."""
        moves = self.search([
            ('rn_exp_kind', 'in', ('lut', 'mixed')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', fields.Date.context_today(self) - relativedelta(years=2)),
        ])
        moves._rn_exp_recompute()
