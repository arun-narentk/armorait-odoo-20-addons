# -*- coding: utf-8 -*-
from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

FY = '2025-26'


@tagged('post_install', '-at_install')
class TestRnGstCalendar(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_calendar.group_rn_gst_calendar_manager').id)]
        cls.Obligation = cls.env['rn.gst.obligation']
        Registration = cls.env['rn.gst.registration']
        company = cls.default_company
        cls.reg_mh_monthly = Registration.create({
            'registration_name': 'Mumbai', 'company_id': company.id, 'gstin': '27DJMPM8965E1ZJ',
            'rn_return_user_id': cls.env.user.id,
        })
        cls.reg_ka_qrmp = Registration.create({
            'registration_name': 'Bengaluru', 'company_id': company.id, 'gstin': '29AAGCC7144L1Z8',
            'rn_filing_frequency': 'quarterly',
        })
        cls.reg_dl_qrmp = Registration.create({
            'registration_name': 'Delhi', 'company_id': company.id, 'gstin': '07AAGCC7144L1ZE',
            'rn_filing_frequency': 'quarterly',
        })
        cls.reg_gj_composition = Registration.create({
            'registration_name': 'Gujarat shop', 'company_id': company.id, 'gstin': '24AABCC7144L1ZN',
            'registration_type': 'composition',
        })

    def _generate(self, registrations):
        return self.Obligation._rn_generate(registrations, FY)

    def _due(self, obligations, code, period):
        return obligations.filtered(lambda o: o.return_type_id.code == code and o.return_period == period)

    def test_monthly_filer(self):
        obligations = self._generate(self.reg_mh_monthly)
        codes = [o.return_type_id.code for o in obligations]
        self.assertEqual(codes.count('GSTR1'), 12)
        self.assertEqual(codes.count('GSTR3B'), 12)
        self.assertNotIn('PMT06', codes)
        self.assertNotIn('GSTR9C', codes)
        self.assertEqual(self._due(obligations, 'GSTR1', '04').due_date, date(2025, 5, 11))
        self.assertEqual(self._due(obligations, 'GSTR3B', '04').due_date, date(2025, 5, 20))
        self.assertEqual(self._due(obligations, 'GSTR3B', '03').due_date, date(2026, 4, 20))
        self.assertEqual(self._due(obligations, 'GSTR9', 'FY').due_date, date(2026, 12, 31))
        self.assertEqual(self._due(obligations, 'GSTR1', '04').user_id, self.env.user)

        # Generating again adds nothing.
        self.assertFalse(self._generate(self.reg_mh_monthly))

        # GSTR-9C only when the GSTIN is marked for it.
        self.reg_mh_monthly.rn_gstr9c_required = True
        extra = self._generate(self.reg_mh_monthly)
        self.assertEqual([o.return_type_id.code for o in extra], ['GSTR9C'])

    def test_qrmp_filer_by_state(self):
        obligations = self._generate(self.reg_ka_qrmp | self.reg_dl_qrmp)
        ka = obligations.filtered(lambda o: o.registration_id == self.reg_ka_qrmp)
        dl = obligations.filtered(lambda o: o.registration_id == self.reg_dl_qrmp)
        self.assertEqual(self._due(ka, 'GSTR1', 'Q1').due_date, date(2025, 7, 13))
        self.assertEqual(self._due(ka, 'GSTR3B', 'Q1').due_date, date(2025, 7, 22))
        self.assertEqual(self._due(dl, 'GSTR3B', 'Q1').due_date, date(2025, 7, 24))
        pmt06 = ka.filtered(lambda o: o.return_type_id.code == 'PMT06')
        self.assertEqual(sorted(pmt06.mapped('return_period')), ['01', '02', '04', '05', '07', '08', '10', '11'])
        self.assertEqual(self._due(ka, 'PMT06', '04').due_date, date(2025, 5, 25))
        self.assertFalse(ka.filtered(lambda o: o.return_type_id.code == 'GSTR1' and o.return_period == '04'))

    def test_composition(self):
        obligations = self._generate(self.reg_gj_composition)
        self.assertEqual(sorted(set(obligations.mapped('return_type_id.code'))), ['CMP08', 'GSTR4'])
        self.assertEqual(self._due(obligations, 'CMP08', 'Q4').due_date, date(2026, 4, 18))
        self.assertEqual(self._due(obligations, 'GSTR4', 'FY').due_date, date(2026, 4, 30))

    def test_extension_moves_due_date(self):
        obligations = self._generate(self.reg_mh_monthly | self.reg_ka_qrmp)
        april_mh = self._due(obligations, 'GSTR3B', '04')
        q1_ka = self._due(obligations, 'GSTR3B', 'Q1')
        gstr3b = self.env.ref('rn_gst_calendar.return_type_gstr3b')
        ext = self.env['rn.gst.due.extension'].create({
            'return_type_id': gstr3b.id, 'financial_year': FY, 'return_period': '04',
            'new_due_date': '2025-05-27', 'state_ids': [(6, 0, self.state_in_mh.ids)],
        })
        self.assertEqual(april_mh.due_date, date(2025, 5, 27))
        self.assertEqual(april_mh.rule_due_date, date(2025, 5, 20))
        self.assertEqual(april_mh.extension_id, ext)

        # An extension for other states does not touch Maharashtra.
        ext.state_ids = [(6, 0, self.state_in_gj.ids)]
        self.assertEqual(april_mh.due_date, date(2025, 5, 20))
        self.assertFalse(april_mh.extension_id)
        ext.unlink()
        self.assertEqual(q1_ka.due_date, date(2025, 7, 22))

    def test_mark_filed_and_days_late(self):
        april = self._due(self._generate(self.reg_mh_monthly), 'GSTR3B', '04')
        april.filed_date = '2025-05-23'
        april.action_mark_filed()
        self.assertEqual(april.state, 'filed')
        self.assertEqual(april.days_late, 3)
        self.assertFalse(april.is_overdue)
        may = self._due(self.Obligation.search([('registration_id', '=', self.reg_mh_monthly.id)]), 'GSTR3B', '05')
        self.assertTrue(may.is_overdue)
        self.assertIn(may, self.Obligation.search([('is_overdue', '=', True)]))
        with self.assertRaises(UserError):
            may.action_mark_not_required()
        may.note = 'Registration surrendered'
        may.action_mark_not_required()
        self.assertEqual(may.days_late, 0)

    def test_reminder_activity(self):
        obligations = self._generate(self.reg_mh_monthly)
        april = self._due(obligations, 'GSTR3B', '04')
        today = date(2025, 5, 17)
        with patch.object(fields.Date, 'context_today', lambda *a, **k: today):
            self.Obligation._cron_rn_calendar()
        self.assertTrue(april.reminder_sent)
        self.assertEqual(april.activity_ids.date_deadline, april.due_date)
        june = self._due(obligations, 'GSTR3B', '06')
        self.assertFalse(june.reminder_sent)

    def test_sync_from_gstr3b(self):
        if 'rn.gst.3b' not in self.env:
            self.skipTest('Armora GST GSTR-3B is not installed.')
        april = self._due(self._generate(self.reg_mh_monthly), 'GSTR3B', '04')
        gstr3b = self.env['rn.gst.3b'].create({
            'company_id': self.default_company.id, 'gstin': self.reg_mh_monthly.gstin,
            'financial_year': FY, 'return_period': '04', 'period_start': '2025-04-01',
            'period_end': '2025-04-30', 'due_date': '2025-05-20',
        })
        gstr3b.action_mark_filed()
        self.Obligation._cron_rn_calendar()
        self.assertEqual(april.state, 'filed')
        self.assertEqual((april.source_model, april.source_id), ('rn.gst.3b', gstr3b.id))
        self.assertEqual(april.filed_date, fields.Date.context_today(april))
