# -*- coding: utf-8 -*-
import re

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

FINDINGS = [
    ('duplicate', 'Duplicate supplier invoice'),
    ('no_ref', 'No supplier invoice number'),
    ('gstin_changed', 'Supplier GSTIN changed'),
    ('over_billed', 'Billed more than received'),
    ('price', 'Price above purchase order'),
    ('tax', 'GST rate differs from purchase order'),
    ('hsn', 'HSN differs from product'),
    ('no_po', 'Goods bill without purchase order'),
]
SEVERITY = {
    'duplicate': 'error', 'over_billed': 'error', 'tax': 'error',
    'no_ref': 'warning', 'gstin_changed': 'warning', 'price': 'warning', 'hsn': 'warning',
    'no_po': 'info',
}


def _norm_ref(ref):
    return re.sub(r'[^A-Z0-9]', '', (ref or '').upper())


class RnGstPurchaseRecon(models.Model):
    _name = 'rn.gst.purchase.recon'
    _description = 'Purchase Reconciliation'
    _inherit = ['mail.thread']
    _order = 'date_to desc, id desc'

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date(required=True, tracking=True)
    date_to = fields.Date(required=True, tracking=True)
    price_tolerance = fields.Float(string='Price Tolerance %', default=1.0,
                                   help='A bill price this much above the purchase order price is accepted.')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Checked')], default='draft', tracking=True)
    line_ids = fields.One2many('rn.gst.purchase.recon.line', 'recon_id', string='Findings')
    bill_count = fields.Integer(string='Bills Checked', readonly=True)
    error_count = fields.Integer(compute='_compute_counts', store=True)
    warning_count = fields.Integer(compute='_compute_counts', store=True)
    open_count = fields.Integer(string='Open Findings', compute='_compute_counts', store=True)
    checked_at = fields.Datetime(readonly=True)

    @api.depends('line_ids.severity', 'line_ids.state')
    def _compute_counts(self):
        for rec in self:
            lines = rec.line_ids
            rec.error_count = len(lines.filtered(lambda l: l.severity == 'error'))
            rec.warning_count = len(lines.filtered(lambda l: l.severity == 'warning'))
            rec.open_count = len(lines.filtered(lambda l: l.state == 'open'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise UserError(_('The end date must be after the start date.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rn.gst.purchase.recon') or _('New')
        return super().create(vals_list)

    def _rn_bills(self):
        self.ensure_one()
        return self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ], order='invoice_date, id')

    def action_run(self):
        for rec in self:
            bills = rec._rn_bills()
            findings = rec._rn_check_bills(bills)
            # Keep review notes of findings that are found again.
            previous = {(l.move_id.id, l.move_line_id.id, l.code): l for l in rec.line_ids}
            for vals in findings:
                old = previous.get((vals['move_id'], vals.get('move_line_id') or False, vals['code']))
                if old and old.state != 'open':
                    vals.update(state=old.state, note=old.note)
            rec.write({
                'line_ids': [Command.clear()] + [Command.create(v) for v in findings],
                'bill_count': len(bills),
                'state': 'done',
                'checked_at': fields.Datetime.now(),
            })
            rec.message_post(body=_('%(bills)s bills checked: %(errors)s errors, %(warnings)s warnings.',
                                    bills=len(bills), errors=rec.error_count, warnings=rec.warning_count))
        return True

    def _rn_check_bills(self, bills):
        self.ensure_one()
        findings = []

        def add(code, move, message, line=None, difference=0.0):
            findings.append({
                'code': code,
                'severity': SEVERITY[code],
                'move_id': move.id,
                'move_line_id': line.id if line else False,
                'message': message,
                'difference': difference,
            })

        # Duplicates are looked for in the whole financial year of each bill, not only this period.
        fy_starts = {b.invoice_date.year if b.invoice_date.month >= 4 else b.invoice_date.year - 1 for b in bills}
        others = self.env['account.move']
        for year in fy_starts:
            others |= self.env['account.move'].search([
                ('company_id', '=', self.company_id.id), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'),
                ('invoice_date', '>=', '%s-04-01' % year), ('invoice_date', '<=', '%s-03-31' % (year + 1)),
            ])
        seen = {}
        for other in others.sorted('id'):
            key = (other.commercial_partner_id.id, _norm_ref(other.ref))
            if key[1]:
                seen.setdefault(key, other)

        for bill in bills:
            partner = bill.commercial_partner_id
            if bill.move_type == 'in_invoice':
                ref = _norm_ref(bill.ref)
                if not ref:
                    add('no_ref', bill, _('No supplier invoice number on the bill.'))
                else:
                    first = seen.get((partner.id, ref))
                    if first and first != bill:
                        add('duplicate', bill, _('Same supplier invoice %(ref)s as bill %(other)s.',
                                                 ref=bill.ref, other=first.name))
            if bill.l10n_in_gstin and partner.vat and bill.l10n_in_gstin != partner.vat:
                add('gstin_changed', bill, _('Bill posted with GSTIN %(old)s, supplier now has %(new)s.',
                                             old=bill.l10n_in_gstin, new=partner.vat))
            goods_without_po = False
            for line in bill.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                pol = line.purchase_line_id
                product = line.product_id
                if product and product.l10n_in_hsn_code and line.l10n_in_hsn_code and \
                        product.l10n_in_hsn_code != line.l10n_in_hsn_code:
                    add('hsn', bill, _('%(product)s: HSN %(line)s on the bill, %(prod)s on the product.',
                                       product=product.display_name, line=line.l10n_in_hsn_code,
                                       prod=product.l10n_in_hsn_code), line=line)
                if not pol:
                    if product and product.type != 'service':
                        goods_without_po = True
                    continue
                if bill.move_type == 'in_invoice' and pol.product_id.type != 'service' and \
                        pol.qty_invoiced - pol.qty_received > 0.0001:
                    add('over_billed', bill, _(
                        '%(product)s on %(po)s: %(billed)s billed, %(received)s received.',
                        product=pol.product_id.display_name, po=pol.order_id.name,
                        billed=pol.qty_invoiced, received=pol.qty_received,
                    ), line=line, difference=(pol.qty_invoiced - pol.qty_received) * pol.price_unit)
                if line.product_uom_id == pol.uom_id and pol.price_unit:
                    limit = pol.price_unit * (1 + self.price_tolerance / 100.0)
                    if line.price_unit > limit:
                        add('price', bill, _(
                            '%(product)s: bill price %(bill)s, purchase order %(po)s price %(price)s.',
                            product=pol.product_id.display_name, bill=line.price_unit, po=pol.order_id.name,
                            price=pol.price_unit,
                        ), line=line, difference=(line.price_unit - pol.price_unit) * line.quantity)
                bill_rates = sorted(line.tax_ids.flatten_taxes_hierarchy().filtered('l10n_in_gst_tax_type').mapped('amount'))
                po_rates = sorted(pol.tax_ids.flatten_taxes_hierarchy().filtered('l10n_in_gst_tax_type').mapped('amount'))
                if bill_rates != po_rates:
                    add('tax', bill, _(
                        '%(product)s: GST %(bill)s%% on the bill, %(po_rates)s%% on %(po)s.',
                        product=pol.product_id.display_name,
                        bill='+'.join('%g' % r for r in bill_rates) or '0',
                        po_rates='+'.join('%g' % r for r in po_rates) or '0', po=pol.order_id.name,
                    ), line=line)
            if goods_without_po and bill.move_type == 'in_invoice':
                add('no_po', bill, _('Goods billed without a purchase order.'))
        return findings


class RnGstPurchaseReconLine(models.Model):
    _name = 'rn.gst.purchase.recon.line'
    _description = 'Purchase Reconciliation Finding'
    _order = 'severity_rank, move_id, id'

    recon_id = fields.Many2one('rn.gst.purchase.recon', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='recon_id.company_id', store=True)
    currency_id = fields.Many2one(related='recon_id.currency_id')
    move_id = fields.Many2one('account.move', string='Bill', required=True, ondelete='cascade', index=True)
    move_line_id = fields.Many2one('account.move.line', string='Bill Line', ondelete='set null')
    partner_id = fields.Many2one(related='move_id.commercial_partner_id', string='Supplier', store=True)
    invoice_date = fields.Date(related='move_id.invoice_date', store=True)
    bill_ref = fields.Char(related='move_id.ref', string='Supplier Invoice')
    code = fields.Selection(FINDINGS, string='Finding', required=True)
    severity = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')], required=True)
    severity_rank = fields.Integer(compute='_compute_severity_rank', store=True)
    message = fields.Char(required=True)
    difference = fields.Monetary(currency_field='currency_id')
    state = fields.Selection([('open', 'Open'), ('reviewed', 'Reviewed'), ('ignored', 'Ignored')], default='open',
                             required=True)
    note = fields.Char()

    @api.depends('severity')
    def _compute_severity_rank(self):
        rank = {'error': 0, 'warning': 1, 'info': 2}
        for line in self:
            line.severity_rank = rank.get(line.severity, 9)

    def action_reviewed(self):
        self.write({'state': 'reviewed'})
        return True

    def action_ignore(self):
        if self.filtered(lambda l: not l.note):
            raise UserError(_('Write a note before ignoring a finding.'))
        self.write({'state': 'ignored'})
        return True

    def action_reopen(self):
        self.write({'state': 'open'})
        return True

    def action_open_bill(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.move_id.id,
                'view_mode': 'form'}
