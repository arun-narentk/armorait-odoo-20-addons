# -*- coding: utf-8 -*-
import base64
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

VALID_GJ = '24ABCPM8965E1ZJ'
VALID_MH = '27DJMPM8965E1ZJ'


@tagged('post_install', '-at_install')
class TestRnGstinVerification(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gstin_verification.group_rn_gstin_verification_manager').id)]
        cls.partner = cls.env['res.partner'].create({
            'name': 'Shree Traders Pvt Ltd',
            'is_company': True,
            'vat': VALID_GJ,
            'country_id': cls.country_in.id,
            'state_id': cls.state_in_gj.id,
        })
        cls.Partner = cls.env['res.partner']

    def _service(self, active=None, error=None):
        """Stand-in for Odoo's IAP GSTIN status call."""
        def fake(partner):
            if error:
                raise UserError(error)
            if active is not None:
                partner.write({
                    'l10n_in_gstin_verified_status': active,
                    'l10n_in_gstin_verified_date': fields.Date.today(),
                })
        return patch.object(type(self.Partner), 'action_l10n_in_verify_gstin_status', fake)

    def test_structure_check(self):
        self.assertEqual(self.partner.rn_gstin_status, 'not_checked')
        self.partner.action_rn_gstin_check()
        check = self.partner.rn_gstin_check_ids
        self.assertEqual((check.method, check.result, check.state_mismatch), ('structure', 'format_ok', False))
        self.assertEqual(self.partner.rn_gstin_status, 'format_ok')
        # Structure OK is not a verification: a re-check is still due.
        self.assertTrue(self.partner.rn_gstin_recheck_due)

        self.partner.vat = '24ABCPM8965E1ZE'
        self.assertEqual(self.partner.rn_gstin_status, 'not_checked')
        self.partner.action_rn_gstin_check()
        self.assertEqual(self.partner.rn_gstin_status, 'format_invalid')
        self.assertFalse(self.partner.rn_gstin_recheck_due)

    def test_state_mismatch(self):
        self.partner.vat = VALID_MH
        self.partner.action_rn_gstin_check()
        check = self.partner.rn_gstin_check_ids[:1]
        self.assertTrue(check.state_mismatch)
        self.assertIn('does not match', check.message)

    def test_status_service_active(self):
        self.env.company.l10n_in_gstin_status_feature = True
        with self._service(active=True):
            self.partner.action_rn_gstin_check()
        portal = self.partner.rn_gstin_check_ids.filtered(lambda c: c.method == 'portal')
        self.assertEqual(portal.result, 'active')
        self.assertEqual(self.partner.rn_gstin_status, 'active')
        self.assertTrue(self.partner.rn_gstin_verified_on)
        self.assertFalse(self.partner.rn_gstin_recheck_due)
        self.assertNotIn(self.partner, self.Partner.search([('rn_gstin_recheck_due', '=', True)]))

    def test_status_service_unreachable_is_not_active(self):
        self.env.company.l10n_in_gstin_status_feature = True
        self.partner.write({'l10n_in_gstin_verified_status': True, 'l10n_in_gstin_verified_date': '2025-01-01'})
        with self._service(error='Unable to connect with GST network'):
            self.partner.action_rn_gstin_check()
        portal = self.partner.rn_gstin_check_ids.filtered(lambda c: c.method == 'portal')
        self.assertEqual(portal.result, 'unavailable')
        self.assertEqual(self.partner.rn_gstin_status, 'unavailable')
        # Odoo's own last result is kept.
        self.assertEqual(str(self.partner.l10n_in_gstin_verified_date), '2025-01-01')

        # No credits: the service does not answer at all.
        with self._service():
            self.partner.action_rn_gstin_check()
        self.assertEqual(self.partner.rn_gstin_check_ids.filtered(lambda c: c.method == 'portal')[:1].result, 'unavailable')

    def test_manual_check_with_proof(self):
        action = self.partner.action_rn_gstin_manual_check()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.result = 'inactive'
        wizard.portal_status = 'Cancelled'
        wizard.legal_name = 'SHREE TRADING COMPANY'
        wizard.proof = base64.b64encode(b'%PDF-1.4 portal screenshot').decode()
        wizard.save().action_save()
        check = self.partner.rn_gstin_check_ids
        self.assertEqual((check.method, check.result, check.name_mismatch), ('manual', 'inactive', True))
        self.assertEqual(check.attachment_id.raw.content, b'%PDF-1.4 portal screenshot')
        self.assertEqual(self.partner.rn_gstin_status, 'inactive')

    def test_names_match(self):
        self.assertTrue(self.Partner._rn_gstin_names_match('M/s. Shree Traders Private Limited', 'Shree Traders Pvt Ltd'))
        self.assertFalse(self.Partner._rn_gstin_names_match('Shree Trading Co', 'Shree Traders Pvt Ltd'))

    def test_recheck_due_after_days(self):
        self.env['rn.gst.gstin.check'].create({
            'partner_id': self.partner.id, 'gstin': VALID_GJ, 'method': 'manual', 'result': 'active',
            'check_date': fields.Datetime.now() - timedelta(days=200),
        })
        self.assertEqual(self.partner.rn_gstin_status, 'active')
        self.assertTrue(self.partner.rn_gstin_recheck_due)
        self.assertIn(self.partner, self.Partner.search([('rn_gstin_recheck_due', '=', True)]))
        self.env.company.rn_gstin_recheck_days = 365
        self.partner.invalidate_recordset(['rn_gstin_recheck_due'])
        self.assertFalse(self.partner.rn_gstin_recheck_due)
        self.assertIn(self.partner, self.Partner.search([('rn_gstin_recheck_due', '=', False)]))

    def test_cron_checks_new_gstins_once(self):
        self.Partner._cron_rn_gstin_structure_check()
        self.assertEqual(len(self.partner.rn_gstin_check_ids), 1)
        self.Partner._cron_rn_gstin_structure_check()
        self.assertEqual(len(self.partner.rn_gstin_check_ids), 1)

    def test_foreign_tax_id_is_not_a_gstin(self):
        foreign = self.env['res.partner'].create({
            'name': 'Wood Corner', 'is_company': True, 'vat': 'US12345672', 'country_id': self.country_us.id,
        })
        self.assertEqual(foreign.rn_gstin_status, 'no_gstin')
        self.Partner._cron_rn_gstin_structure_check()
        self.assertFalse(foreign.rn_gstin_check_ids)
        with self.assertRaises(UserError):
            foreign.action_rn_gstin_check()

    def test_check_without_gstin(self):
        with self.assertRaises(UserError):
            self.env['res.partner'].create({'name': 'No GST'}).action_rn_gstin_check()
