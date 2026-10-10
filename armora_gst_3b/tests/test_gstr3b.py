# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGst3b(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('armora_gst_base.group_armora_gst_administrator').id)]
        cls.default_company.vat = '24AAACB6992P1Z3'

    def _create_3b(self):
        return self.env['armora.gst.3b'].create({
            'company_id': self.default_company.id,
            'gstin': self.default_company.vat,
            'financial_year': '2025-26',
            'return_period': '01',
            'period_start': '2026-01-01',
            'period_end': '2026-01-31',
            'due_date': '2026-02-20',
            'payment_date': '2026-03-05',
            'net_tax_liability': 100000.0,
            'minimum_ecl_balance': 40000.0,
            'interest_rate': 0.18,
        })

    def test_gstr3b_interest_with_ecl(self):
        Calculator = self.env['armora.gst.interest.calculator']
        result = Calculator.calculate({
            'return_period': '202601',
            'due_date': '2026-02-20',
            'payment_date': '2026-03-05',
            'net_tax_liability': 100000,
            'minimum_ecl_balance': 40000,
            'interest_rate': 0.18,
        })
        # days = 13, base = 60000, interest = 60000 * 13/365 * 0.18
        expected = round(60000 * 13 / 365 * 0.18, 2)
        self.assertAlmostEqual(result['system_minimum_interest'], expected, places=2)
        self.assertEqual(result['calculation_version'], '2026.01')

    def test_self_assessed_higher_ok(self):
        Calculator = self.env['armora.gst.interest.calculator']
        result = Calculator.calculate({
            'return_period': '202601',
            'due_date': '2026-02-20',
            'payment_date': '2026-03-05',
            'net_tax_liability': 100000,
            'minimum_ecl_balance': 40000,
            'interest_rate': 0.18,
            'self_assessed_interest': 500.0,
        })
        self.assertGreaterEqual(result['self_assessed_interest'], result['system_minimum_interest'])

    def test_self_assessed_lower_blocked(self):
        Calculator = self.env['armora.gst.interest.calculator']
        with self.assertRaises(ValidationError):
            Calculator.calculate({
                'return_period': '202601',
                'due_date': '2026-02-20',
                'payment_date': '2026-03-05',
                'net_tax_liability': 100000,
                'minimum_ecl_balance': 0,
                'interest_rate': 0.18,
                'self_assessed_interest': 0.01,
            })

    def test_liability_breakup_previous_period(self):
        filing = self._create_3b()
        line = self.env['armora.gst.3b.liability.breakup'].create({
            'filing_id': filing.id,
            'source_period': '202512',
            'reporting_period': '202601',
            'document_date': '2025-12-15',
            'taxable_value': 1000,
            'igst': 180,
            'source_return': 'gstr1',
            'source_table': 'B2B',
        })
        self.assertEqual(line.source_return, 'gstr1')
        with self.assertRaises(ValidationError):
            self.env['armora.gst.3b.liability.breakup'].create({
                'filing_id': filing.id,
                'source_period': '202601',
                'reporting_period': '202601',
                'source_return': 'gstr1',
            })

    def test_itc_utilization_legal(self):
        Engine = self.env['armora.gst.itc.utilization']
        result = Engine.utilize({
            'on_date': '2026-01-15',
            'return_period': '202601',
            'opening_itc': {'igst': 1000, 'cgst': 500, 'sgst': 500, 'cess': 0},
            'itc_available': {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0},
            'liabilities': {'igst': 800, 'cgst': 200, 'sgst': 200, 'cess': 0},
        })
        self.assertEqual(result['rule_version'], '2026.01')
        self.assertAlmostEqual(result['cash_payable']['igst'], 0.0, places=2)

    def test_itc_illegal_cess_cross(self):
        Engine = self.env['armora.gst.itc.utilization']
        # CESS ITC must not reduce IGST cash payable
        result = Engine.utilize({
            'on_date': '2026-01-15',
            'return_period': '202601',
            'opening_itc': {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 500},
            'itc_available': {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0},
            'liabilities': {'igst': 200, 'cgst': 0, 'sgst': 0, 'cess': 0},
        })
        self.assertAlmostEqual(result['cash_payable']['igst'], 200.0, places=2)
        self.assertAlmostEqual(result['itc_remaining']['cess'], 500.0, places=2)

    def test_filed_readonly(self):
        filing = self._create_3b()
        filing.action_mark_filed()
        with self.assertRaises(UserError):
            filing.write({'net_tax_liability': 1.0})

    def test_multi_company_interest_rule(self):
        Calculator = self.env['armora.gst.interest.calculator']
        result = Calculator.calculate({
            'return_period': '202601',
            'due_date': '2026-02-20',
            'payment_date': '2026-02-20',
            'net_tax_liability': 1000,
            'minimum_ecl_balance': 0,
        })
        self.assertEqual(result['system_minimum_interest'], 0.0)

    def test_interest_recompute(self):
        Calculator = self.env['armora.gst.interest.calculator']
        payload = {
            'return_period': '202601',
            'due_date': '2026-02-20',
            'payment_date': '2026-03-05',
            'net_tax_liability': 100000,
            'minimum_ecl_balance': 40000,
            'interest_rate': 0.18,
        }
        first = Calculator.calculate(payload)
        second = Calculator.recompute(payload)
        self.assertTrue(second.get('recomputed'))
        self.assertAlmostEqual(
            second['system_minimum_interest'],
            first['system_minimum_interest'],
            places=2,
        )

    def test_recompute_interest_action(self):
        filing = self._create_3b()
        filing.action_compute_interest()
        filing.action_recompute_interest()
        self.assertGreaterEqual(filing.self_assessed_interest, filing.system_minimum_interest)
