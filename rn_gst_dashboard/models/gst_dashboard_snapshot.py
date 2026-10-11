# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstDashboardSnapshot(models.Model):
    """Optional stored snapshot of dashboard aggregates.

    Skeleton only. Refresh rules and payload structure are defined in later
    steps. When used, the UI must show that values may be cached.
    """

    _name = 'rn.gst.dashboard.snapshot'
    _description = 'GST Dashboard Snapshot'
    _order = 'captured_at desc, id desc'

    name = fields.Char(required=True, default='Snapshot')
    dashboard_id = fields.Many2one(
        'rn.gst.dashboard',
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    gstin = fields.Char(index=True)
    financial_year = fields.Char()
    return_period = fields.Char()
    date_from = fields.Date()
    date_to = fields.Date()
    captured_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    captured_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
    )
    payload_json = fields.Text(
        help='Serialized aggregate payload (structure defined in later steps).',
    )
    is_stale = fields.Boolean(
        default=False,
        help='Set when source data may have changed after capture.',
    )
    notes = fields.Text()
