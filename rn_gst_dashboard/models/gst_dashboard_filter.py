# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstDashboardFilter(models.Model):
    """Saved dashboard filter preset (manager configuration).

    Skeleton for named filter sets. Runtime filter entry uses the wizard.
    """

    _name = 'rn.gst.dashboard.filter'
    _description = 'GST Dashboard Filter Preset'
    _order = 'name'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    gst_registration_id = fields.Many2one(
        'rn.gst.registration',
        domain="[('company_id', '=', company_id)]",
    )
    gstin = fields.Char()
    financial_year = fields.Char()
    return_period = fields.Char()
    date_from = fields.Date()
    date_to = fields.Date()
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        index=True,
    )
    notes = fields.Text()
