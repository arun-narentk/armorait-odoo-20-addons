# -*- coding: utf-8 -*-
import json
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RnGstRule(models.Model):
    """Versioned GSTN / statutory rule definitions.

    Validation and calculators must resolve rules by transaction date,
    return period and API version instead of hard-coding behaviour.
    """

    _name = 'rn.gst.rule'
    _description = 'Armora GST Rule'
    _order = 'rule_code, effective_from desc, version desc'

    name = fields.Char(required=True)
    rule_code = fields.Char(required=True, index=True)
    rule_type = fields.Selection(
        selection=[
            ('einvoice', 'E-Invoice'),
            ('ewaybill', 'E-Way Bill'),
            ('gstr3b', 'GSTR-3B'),
            ('itc', 'ITC Utilization'),
            ('validation', 'Validation'),
            ('other', 'Other'),
        ],
        required=True,
        default='validation',
    )
    effective_from = fields.Date(required=True)
    effective_to = fields.Date(
        help='Leave empty for open-ended rules.',
    )
    active = fields.Boolean(default=True)
    version = fields.Char(required=True, default='1.0')
    api_version = fields.Char(
        help='Optional GSTN / GSP API version this rule applies to.',
    )
    description = fields.Text()
    configuration = fields.Text(
        string='Configuration (JSON)',
        help='Rule parameters as JSON. Keep statutory logic versioned here.',
        default='{}',
    )
    source_reference = fields.Char(
        help='Advisory / notification reference, e.g. GSTN 17.06.2026.',
    )

    _rn_gst_rule_code_version_uniq = models.Constraint(
        'unique(rule_code, version, effective_from)',
        "Rule code + version + effective_from must be unique.",
    )

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for rule in self:
            if rule.effective_to and rule.effective_to < rule.effective_from:
                raise ValidationError(_('effective_to cannot be before effective_from.'))

    @api.constrains('configuration')
    def _check_configuration_json(self):
        for rule in self:
            raw = (rule.configuration or '').strip() or '{}'
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as err:
                raise ValidationError(_('Rule configuration must be valid JSON.')) from err
            if not isinstance(data, dict):
                raise ValidationError(_('Rule configuration JSON must be an object.'))

    def get_config(self):
        self.ensure_one()
        raw = (self.configuration or '').strip() or '{}'
        return json.loads(raw)

    @api.model
    def find_applicable(
        self,
        rule_code,
        on_date=None,
        api_version=None,
        return_period=None,
    ):
        """Return the newest active rule matching date / API version."""
        on_date = on_date or fields.Date.context_today(self)
        if isinstance(on_date, str):
            on_date = fields.Date.to_date(on_date)
        domain = [
            ('rule_code', '=', rule_code),
            ('active', '=', True),
            ('effective_from', '<=', on_date),
            '|',
            ('effective_to', '=', False),
            ('effective_to', '>=', on_date),
        ]
        # Rule configuration is shared suite metadata; lookup must not depend on
        # the caller's ACLs (invoice posting / API prechecks run as many users).
        rules = self.sudo().search(domain, order='effective_from desc, version desc')
        if api_version:
            # Empty filtered set must win (do not fall back to a mismatched version).
            rules = rules.filtered(
                lambda r: not r.api_version or r.api_version == api_version
            )
        if return_period and rules:
            # Optional filter via configuration key applicable_from_period (YYYYMM)
            filtered = self.env['rn.gst.rule']
            for rule in rules:
                cfg = rule.get_config()
                from_period = cfg.get('applicable_from_period')
                if not from_period or str(return_period) >= str(from_period):
                    filtered |= rule
            rules = filtered
        return rules[:1]

    @api.model
    def rule_applies(self, rule_code, on_date=None, **kwargs):
        return bool(self.find_applicable(rule_code, on_date=on_date, **kwargs))
