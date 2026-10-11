# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    # The variant form reuses the template form, so its buttons land here.
    def action_copy_record_link(self):
        self.ensure_one()
        return self.product_tmpl_id.action_copy_record_link()

    def action_open_record_share(self):
        self.ensure_one()
        return self.product_tmpl_id.action_open_record_share()

    def action_open_record_qr(self):
        self.ensure_one()
        return self.product_tmpl_id.action_open_record_qr()
