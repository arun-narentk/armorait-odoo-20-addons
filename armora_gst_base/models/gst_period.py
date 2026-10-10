# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..exceptions import GstPeriodError
from ..services import periods as period_service


class ArmoraGstPeriod(models.AbstractModel):
    """Indian financial year and GST return period helpers."""

    _name = 'armora.gst.period'
    _description = 'Armora GST Period Helpers'

    @api.model
    def fy_start_year(self, financial_year):
        """Parse '2025-26' -> 2025."""
        try:
            return period_service.fy_start_year(financial_year)
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err

    @api.model
    def compute_period_dates(self, financial_year, return_period, frequency='monthly'):
        """Return (period_start, period_end) dates for monthly or quarterly GST periods."""
        try:
            return period_service.compute_period_dates(
                financial_year, return_period, frequency=frequency
            )
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err

    @api.model
    def current_financial_year(self, on_date=None):
        """Return FY label like 2025-26 for a given date (default today)."""
        try:
            return period_service.get_financial_year(on_date)
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err

    @api.model
    def get_return_period(self, on_date=None, frequency='monthly'):
        try:
            return period_service.get_return_period(on_date, frequency=frequency)
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err

    @api.model
    def get_period_start(self, financial_year, return_period, frequency='monthly'):
        try:
            return period_service.get_period_start(
                financial_year, return_period, frequency=frequency
            )
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err

    @api.model
    def get_period_end(self, financial_year, return_period, frequency='monthly'):
        try:
            return period_service.get_period_end(
                financial_year, return_period, frequency=frequency
            )
        except GstPeriodError as err:
            raise ValidationError(_('%s') % err) from err
