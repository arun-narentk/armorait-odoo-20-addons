# -*- coding: utf-8 -*-
"""Dashboard JSON route."""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class RnHallDashboardController(http.Controller):

    @http.route('/rn_hall_base/dashboard/data', type='jsonrpc', auth='user')
    def dashboard_data(self):
        payload = request.env['rn.hall.dashboard.service'].get_dashboard_data()
        return payload
