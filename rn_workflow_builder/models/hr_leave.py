# -*- coding: utf-8 -*-

from odoo import models


class HrLeave(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'rn.workflow.mixin']
