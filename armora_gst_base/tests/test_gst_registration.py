# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestArmoraGstRegistration(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Registration = cls.env['armora.gst.registration']
        cls.state_gj = cls.env.ref('base.state_in_gj')
        cls.state_mh = cls.env.ref('base.state_in_mh')
        cls.state_tn = cls.env.ref('base.state_in_tn')
        cls.state_ka = cls.env.ref('base.state_in_ka')

        # Fictional GSTINs with valid structure/checksum (local algorithm).
        cls.gstin_gj = '24AABCT1332L1ZK'
        cls.gstin_mh = '27AABCM7777C1ZB'
        cls.gstin_tn = '33AABCT5555D1ZL'
        cls.gstin_ka = '29AABCK9999A1Z1'

        cls.env.user.group_ids = [
            (4, cls.env.ref('armora_gst_base.group_armora_gst_administrator').id),
        ]

    def _create_registration(self, **kwargs):
        vals = {
            'registration_name': 'Test Registration',
            'company_id': self.default_company.id,
            'gstin': self.gstin_gj,
            'state_id': self.state_gj.id,
            'state_code': '24',
            'registration_type': 'regular',
            'active': True,
            'effective_from': date(2024, 4, 1),
        }
        vals.update(kwargs)
        return self.Registration.create(vals)

    def test_create_valid_registration(self):
        reg = self._create_registration(
            registration_name='Gujarat HO',
            legal_name='Armora Technologies Pvt Ltd',
            trade_name='Armora Tech',
        )
        self.assertEqual(reg.gstin, self.gstin_gj)
        self.assertEqual(reg.state_code, '24')
        self.assertEqual(reg.state_id, self.state_gj)
        self.assertIn(self.gstin_gj, reg.display_name)

    def test_gstin_normalization(self):
        reg = self._create_registration(gstin=' 24aabct1332l1zk ')
        self.assertEqual(reg.gstin, self.gstin_gj)

    def test_required_fields(self):
        with self.assertRaises(Exception):
            self.Registration.create({
                'company_id': self.default_company.id,
                'gstin': self.gstin_gj,
            })

    def test_invalid_gstin_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_registration(gstin='24AAGCC7144L6ZE')

    def test_state_gstin_mismatch(self):
        with self.assertRaises(ValidationError):
            self._create_registration(
                gstin=self.gstin_gj,
                state_id=self.state_mh.id,
                state_code='27',
            )

    def test_duplicate_active_gstin_same_company(self):
        self._create_registration(registration_name='Primary')
        with self.assertRaises(ValidationError):
            self._create_registration(registration_name='Duplicate')

    def test_inactive_allows_same_gstin(self):
        first = self._create_registration(registration_name='Old')
        first.active = False
        second = self._create_registration(registration_name='New')
        self.assertTrue(second.active)
        self.assertFalse(first.active)

    def test_effective_dates(self):
        with self.assertRaises(ValidationError):
            self._create_registration(
                effective_from=date(2025, 4, 1),
                effective_to=date(2025, 3, 31),
            )

    def test_auto_state_from_gstin(self):
        reg = self.Registration.create({
            'registration_name': 'Maharashtra Branch',
            'company_id': self.default_company.id,
            'gstin': self.gstin_mh,
            'registration_type': 'regular',
        })
        self.assertEqual(reg.state_code, '27')
        self.assertEqual(reg.state_id, self.state_mh)

    def test_multi_company_record_rule(self):
        other_company = self._create_company(
            name='Other IN Company',
            country_id=self.country_in.id,
            state_id=self.state_tn.id,
        )
        reg_a = self._create_registration(
            registration_name='Company A TN',
            gstin=self.gstin_tn,
            state_id=self.state_tn.id,
            state_code='33',
        )
        reg_b = self.Registration.with_company(other_company).create({
            'registration_name': 'Company B KA',
            'company_id': other_company.id,
            'gstin': self.gstin_ka,
            'state_id': self.state_ka.id,
            'state_code': '29',
            'registration_type': 'regular',
        })

        user_a = self.env['res.users'].create({
            'name': 'GST User A',
            'login': 'armora_gst_user_a_%s' % self.default_company.id,
            'company_id': self.default_company.id,
            'company_ids': [(6, 0, [self.default_company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('armora_gst_base.group_armora_gst_user').id,
            ])],
        })
        visible = self.Registration.with_user(user_a).search([])
        self.assertIn(reg_a, visible)
        self.assertNotIn(reg_b, visible)

        with self.assertRaises(AccessError):
            reg_b.with_user(user_a).read(['registration_name'])
