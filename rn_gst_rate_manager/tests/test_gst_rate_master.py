# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'rn_gst_rate')
class TestRnGstRateMaster(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Rate = self.env['rn.gst.rate']
        self.company = self.env.company

    def test_create_rate_with_components(self):
        rate = self.Rate.create({
            'name': 'GST 18%',
            'code': 'GST_18',
            'igst_rate': 18.0,
            'cgst_rate': 9.0,
            'sgst_rate': 9.0,
            'effective_from': '2024-04-01',
            'state': 'draft',
        })
        self.assertEqual(rate.total_gst_rate, 18.0)
        self.assertEqual(rate.company_id, self.company)

    def test_invalid_date_range(self):
        with self.assertRaises(ValidationError):
            self.Rate.create({
                'name': 'Bad dates',
                'code': 'GST_BAD_DATE',
                'igst_rate': 5.0,
                'cgst_rate': 2.5,
                'sgst_rate': 2.5,
                'effective_from': '2025-01-10',
                'effective_to': '2025-01-01',
            })

    def test_component_mismatch(self):
        with self.assertRaises(ValidationError):
            self.Rate.create({
                'name': 'Mismatch',
                'code': 'GST_MISMATCH',
                'igst_rate': 18.0,
                'cgst_rate': 9.0,
                'sgst_rate': 5.0,
                'effective_from': '2024-04-01',
            })

    def test_overlap_active_versions(self):
        self.Rate.create({
            'name': 'GST 12% A',
            'code': 'GST_12',
            'igst_rate': 12.0,
            'cgst_rate': 6.0,
            'sgst_rate': 6.0,
            'effective_from': '2024-04-01',
            'effective_to': False,
            'state': 'active',
        })
        with self.assertRaises(ValidationError):
            self.Rate.create({
                'name': 'GST 12% B',
                'code': 'GST_12',
                'igst_rate': 12.0,
                'cgst_rate': 6.0,
                'sgst_rate': 6.0,
                'effective_from': '2025-01-01',
                'state': 'active',
            })

    def test_non_overlapping_versions_ok(self):
        first = self.Rate.create({
            'name': 'GST 5% old',
            'code': 'GST_5',
            'igst_rate': 5.0,
            'cgst_rate': 2.5,
            'sgst_rate': 2.5,
            'effective_from': '2023-04-01',
            'effective_to': '2024-03-31',
            'state': 'active',
        })
        second = self.Rate.create({
            'name': 'GST 5% new',
            'code': 'GST_5',
            'igst_rate': 5.0,
            'cgst_rate': 2.5,
            'sgst_rate': 2.5,
            'effective_from': '2024-04-01',
            'state': 'active',
        })
        self.assertTrue(first.id)
        self.assertTrue(second.id)

    def test_historical_rate_not_rewritten(self):
        rate = self.Rate.create({
            'name': 'GST 28% history',
            'code': 'GST_28',
            'igst_rate': 28.0,
            'cgst_rate': 14.0,
            'sgst_rate': 14.0,
            'effective_from': '2020-04-01',
            'effective_to': '2021-03-31',
            'state': 'expired',
        })
        with self.assertRaises(ValidationError):
            rate.write({'igst_rate': 18.0, 'cgst_rate': 9.0, 'sgst_rate': 9.0})

    def test_get_rate_for_date(self):
        self.Rate.create({
            'name': 'GST 18% FY',
            'code': 'GST_18_LOOKUP',
            'igst_rate': 18.0,
            'cgst_rate': 9.0,
            'sgst_rate': 9.0,
            'effective_from': '2024-04-01',
            'effective_to': '2025-03-31',
            'state': 'active',
        })
        found = self.Rate.get_rate_for_date(
            self.company, 'GST_18_LOOKUP', on_date=fields.Date.to_date('2024-06-15'),
        )
        self.assertTrue(found)
        self.assertEqual(found.code, 'GST_18_LOOKUP')
        missing = self.Rate.get_rate_for_date(
            self.company, 'GST_18_LOOKUP', on_date=fields.Date.to_date('2026-01-01'),
        )
        self.assertFalse(missing)

    def test_no_utgst_field(self):
        self.assertNotIn('utgst_rate', self.Rate._fields)
