# -*- coding: utf-8 -*-
from odoo import api, models

from ..services import monetary as money_service


class RnGstMoney(models.AbstractModel):
    """Decimal-safe monetary helpers for GST calculations."""

    _name = 'rn.gst.money'
    _description = 'Armora GST Money Helpers'

    @api.model
    def round_amount(self, amount, currency=None, precision_digits=None):
        if precision_digits is None:
            precision_digits = currency.decimal_places if currency else 2
        return money_service.round_amount(amount, precision_digits=precision_digits)

    @api.model
    def compare_amounts(self, left, right, tolerance=0, currency=None, precision_digits=None):
        if precision_digits is None:
            precision_digits = currency.decimal_places if currency else 2
        return money_service.compare_tax_amounts_with_tolerance(
            left, right, tolerance=tolerance, precision_digits=precision_digits
        )
