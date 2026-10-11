# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    def action_view_smart_notes(self):
        # The variant form reuses the template form, so its button lands here.
        self.ensure_one()
        return self.product_tmpl_id.action_view_smart_notes()
