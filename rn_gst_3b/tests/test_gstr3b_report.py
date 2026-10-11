# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGst3bReport(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_base.group_rn_gst_administrator').id)]
        cls.default_company.vat = '24AAACB6992P1Z3'

    def test_gstr3b_summary_pdf(self):
        gstr3b = self.env['rn.gst.3b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '04',
            'period_start': '2025-04-01',
            'period_end': '2025-04-30',
            'due_date': '2025-05-20',
            'liability_igst': 1000.0,
            'liability_cgst': 500.0,
            'liability_sgst': 500.0,
            'itc_available_igst': 600.0,
            'itc_available_cgst': 200.0,
            'itc_available_sgst': 200.0,
        })
        gstr3b.action_compute_itc_utilization()
        html = self.env['ir.actions.report']._render_qweb_html(
            'rn_gst_3b.report_gstr3b_summary', gstr3b.ids,
        )[0].decode()
        self.assertIn('GSTR-3B Summary', html)
        self.assertIn('Payment of tax (Table 6.1)', html)
        self.assertIn(gstr3b.name, html)
        self.assertIn('No previous-period supplies in this return.', html)
