# -*- coding: utf-8 -*-
from odoo import fields, models


class RnGstEwaybillMixin(models.AbstractModel):
    """Shared EWB lifecycle / closure fields."""

    _name = 'rn.gst.ewaybill.mixin'
    _description = 'Armora GST E-Way Bill Mixin'

    def _valid_field_parameter(self, field, name):
        # Tracking is applied by mail.thread on the models using this mixin.
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    rn_ewb_number = fields.Char(string='E-Way Bill Number', copy=False, tracking=True, index=True)
    rn_ewb_irn = fields.Char(string='EWB IRN', copy=False, tracking=True)
    rn_ewb_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('cancelled', 'Cancelled'),
            ('discarded', 'Discarded'),
            ('closed', 'Closed'),
        ],
        string='EWB Status',
        default='draft',
        copy=False,
        tracking=True,
        help='Includes proposed GSTN Closed status. During stabilisation Active/Cancelled/Discarded may still be returned by API.',
    )
    rn_ewb_generation_date = fields.Datetime(string='EWB Generation Date', copy=False, tracking=True)
    rn_ewb_validity_date = fields.Datetime(string='EWB Valid Until', copy=False, tracking=True)
    rn_ewb_vehicle_no = fields.Char(string='EWB Vehicle Number', copy=False)
    rn_ewb_transporter_id = fields.Many2one('res.partner', string='EWB Transporter', copy=False)
    rn_ewb_delivery_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
        ],
        string='Delivery Status (EWB)',
        default='pending',
        copy=False,
        help='Operational delivery marker for closure checks. Independent of stock picking state.',
    )
    rn_ewb_closure_status = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('requested', 'Closure Requested'),
            ('closed', 'Closed'),
            ('failed', 'Closure Failed'),
        ],
        string='Closure Status',
        default='open',
        copy=False,
        tracking=True,
    )
    rn_ewb_closure_requested = fields.Boolean(string='Closure Requested', copy=False)
    rn_ewb_closure_date = fields.Date(string='Closure Date', copy=False, tracking=True)
    rn_ewb_closure_remarks = fields.Char(string='Closure Remarks', copy=False)
    rn_ewb_closure_user_id = fields.Many2one('res.users', string='Closed By', copy=False)
    rn_ewb_closure_timestamp = fields.Datetime(string='Closure Timestamp', copy=False)
    rn_ewb_closure_response = fields.Text(string='Closure Response', copy=False)
    rn_ewb_closure_error = fields.Text(string='Closure Error', copy=False)
    rn_ewb_closure_api_reference = fields.Char(string='Closure API Reference', copy=False)
