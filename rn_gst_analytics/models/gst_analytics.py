# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

TAX_TAGS = ('igst', 'cgst', 'sgst', 'cess')


class RnGstAnalytics(models.Model):
    """Taxable value and GST of posted journal items, read from the l10n_in GST tax tags.

    One row per base line (its taxable value, counted once even when the line carries
    CGST and SGST) and one row per GST tax line.
    """

    _name = 'rn.gst.analytics'
    _description = 'GST Analytics'
    _auto = False
    _order = 'date desc'
    _rec_name = 'move_id'

    date = fields.Date(readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    journal_id = fields.Many2one('account.journal', readonly=True)
    move_id = fields.Many2one('account.move', string='Document', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    direction = fields.Selection([
        ('outward', 'Outward (Sales)'),
        ('inward', 'Inward (Purchases)'),
        ('other', 'Other Entries'),
    ], readonly=True)
    kind = fields.Selection([('taxable', 'Taxable Value'), ('tax', 'GST')], readonly=True)
    head = fields.Selection([
        ('igst', 'IGST'),
        ('cgst', 'CGST'),
        ('sgst', 'SGST/UTGST'),
        ('cess', 'Cess'),
        ('cgst_sgst', 'CGST + SGST'),
    ], string='Tax Head', readonly=True)
    gstr_section = fields.Selection(
        selection=lambda self: self.env['account.move.line']._fields['l10n_in_gstr_section'].selection,
        string='GSTR Section', readonly=True,
    )
    taxable_amount = fields.Monetary(string='Taxable Value', readonly=True, currency_field='currency_id')
    tax_amount = fields.Monetary(string='GST', readonly=True, currency_field='currency_id')
    output_tax = fields.Monetary(string='Output GST', readonly=True, currency_field='currency_id')
    input_tax = fields.Monetary(string='Input GST', readonly=True, currency_field='currency_id')

    @api.model
    def _rn_tag_ids(self):
        tags = {}
        for head in TAX_TAGS:
            for prefix in ('tax_tag_', 'tax_tag_base_'):
                tag = self.env.ref('l10n_in.%s%s' % (prefix, head), raise_if_not_found=False)
                tags['%s%s' % ('base_' if 'base' in prefix else '', head)] = tag.id if tag else 0
        return tags

    def init(self):
        tags = self._rn_tag_ids()
        tools.drop_view_if_exists(self.env.cr, self._table)
        base_ids = tuple(tags['base_%s' % h] for h in TAX_TAGS) or (0,)
        sign = "CASE WHEN j.type = 'sale' THEN -aml.balance ELSE aml.balance END"
        direction = "CASE j.type WHEN 'sale' THEN 'outward' WHEN 'purchase' THEN 'inward' ELSE 'other' END"
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    aml.id * 10 AS id,
                    aml.date, aml.company_id, aml.company_currency_id AS currency_id, aml.journal_id, aml.move_id,
                    aml.partner_id, {direction} AS direction, 'taxable' AS kind,
                    CASE WHEN bool_or(rel.account_account_tag_id = %(base_igst)s) THEN 'igst' ELSE 'cgst_sgst' END AS head,
                    aml.l10n_in_gstr_section AS gstr_section,
                    {sign} AS taxable_amount,
                    0.0 AS tax_amount, 0.0 AS output_tax, 0.0 AS input_tax
                FROM account_move_line aml
                JOIN account_move m ON m.id = aml.move_id AND m.state = 'posted'
                JOIN account_journal j ON j.id = aml.journal_id
                JOIN account_account_tag_account_move_line_rel rel ON rel.account_move_line_id = aml.id
                WHERE rel.account_account_tag_id IN %(base_ids)s
                GROUP BY aml.id, j.type
            UNION ALL
                SELECT
                    aml.id * 10 + 1 + tag_head.n AS id,
                    aml.date, aml.company_id, aml.company_currency_id AS currency_id, aml.journal_id, aml.move_id,
                    aml.partner_id, {direction} AS direction, 'tax' AS kind,
                    tag_head.head, aml.l10n_in_gstr_section AS gstr_section,
                    0.0 AS taxable_amount,
                    {sign} AS tax_amount,
                    CASE WHEN j.type = 'sale' THEN {sign} ELSE 0.0 END AS output_tax,
                    CASE WHEN j.type = 'purchase' THEN {sign} ELSE 0.0 END AS input_tax
                FROM account_move_line aml
                JOIN account_move m ON m.id = aml.move_id AND m.state = 'posted'
                JOIN account_journal j ON j.id = aml.journal_id
                JOIN account_account_tag_account_move_line_rel rel ON rel.account_move_line_id = aml.id
                JOIN (VALUES (%(igst)s, 'igst', 0), (%(cgst)s, 'cgst', 1), (%(sgst)s, 'sgst', 2), (%(cess)s, 'cess', 3))
                    AS tag_head(tag_id, head, n) ON tag_head.tag_id = rel.account_account_tag_id
                LEFT JOIN account_tax tax ON tax.id = aml.tax_line_id
                -- On a reverse charge sale the customer pays the GST: it is not our output tax.
                WHERE NOT (j.type = 'sale' AND COALESCE(tax.l10n_in_reverse_charge, FALSE))
            )
        """, dict(tags, base_ids=base_ids))
