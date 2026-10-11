# -*- coding: utf-8 -*-

from odoo import models


class StockWarehouseOrderpoint(models.Model):
    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'rn.workflow.mixin']
