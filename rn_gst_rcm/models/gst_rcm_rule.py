# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RnGstRcmRule(models.Model):
    """A supply on which the recipient pays GST under reverse charge."""

    _name = 'rn.gst.rcm.rule'
    _description = 'Reverse Charge Rule'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', help='Leave empty to use the rule in every company.')
    section = fields.Selection([
        ('9_3', 'Section 9(3): notified supplies'),
        ('9_4', 'Section 9(4): supplies from unregistered persons'),
        ('import', 'Import of services'),
    ], required=True, default='9_3')
    supplier_condition = fields.Selection([
        ('any', 'Any supplier'),
        ('unregistered', 'Unregistered suppliers only'),
        ('registered', 'Registered suppliers only'),
    ], required=True, default='any')
    product_ids = fields.Many2many('product.product', string='Products')
    categ_ids = fields.Many2many('product.category', string='Product Categories',
                                 help='Products in these categories and their sub-categories.')
    account_ids = fields.Many2many('account.account', string='Expense Accounts')
    tax_intra_id = fields.Many2one(
        'account.tax', string='Tax, Same State', domain="[('type_tax_use', '=', 'purchase'), ('l10n_in_reverse_charge', '=', True)]",
        help='Reverse charge tax when the supplier is in the same state, e.g. 5% GST RC.',
    )
    tax_inter_id = fields.Many2one(
        'account.tax', string='Tax, Other State', domain="[('type_tax_use', '=', 'purchase'), ('l10n_in_reverse_charge', '=', True)]",
        help='Reverse charge tax when the supplier is in another state or abroad, e.g. 5% IGST RC.',
    )
    note = fields.Text(help='Conditions to check, e.g. the notification entry and when the supplier may opt for forward charge.')

    @api.model
    def _rn_rule_for_line(self, line):
        """First active rule that covers a vendor bill line, or an empty recordset."""
        company = line.move_id.company_id
        for rule in self.search(['|', ('company_id', '=', False), ('company_id', '=', company.id)]):
            if not rule._rn_supplier_matches(line.move_id):
                continue
            product = line.product_id
            if product and product in rule.product_ids:
                return rule
            if product and rule.categ_ids and product.categ_id.parent_path and any(
                product.categ_id.parent_path.startswith(categ.parent_path) for categ in rule.categ_ids if categ.parent_path
            ):
                return rule
            if line.account_id and line.account_id in rule.account_ids:
                return rule
        return self.browse()

    def _rn_supplier_matches(self, move):
        self.ensure_one()
        unregistered = move.l10n_in_gst_treatment in ('unregistered', 'consumer')
        if self.supplier_condition == 'unregistered':
            return unregistered
        if self.supplier_condition == 'registered':
            return not unregistered and move.l10n_in_gst_treatment != 'overseas'
        return True

    def _rn_tax_for_move(self, move):
        self.ensure_one()
        partner_state = move.commercial_partner_id.state_id
        same_state = (
            move.l10n_in_gst_treatment != 'overseas'
            and partner_state and partner_state == move.company_id.state_id
        )
        return (self.tax_intra_id if same_state else self.tax_inter_id) or self.tax_inter_id or self.tax_intra_id
