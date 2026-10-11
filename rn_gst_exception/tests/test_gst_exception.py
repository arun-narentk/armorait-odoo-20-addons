# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstException(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [(4, cls.env.ref('rn_gst_exception.group_rn_gst_exception_manager').id)]
        cls.Exception = cls.env['rn.gst.exception']

    def _finding(self, key, **vals):
        return dict({
            'fingerprint': key,
            'company_id': self.default_company.id,
            'title': 'Problem %s' % key,
            'severity': 'error',
        }, **vals)

    def test_manual_exception_owner_gets_activity(self):
        exc = self.Exception.create({
            'title': 'Supplier GSTIN wrong',
            'user_id': self.env.user.id,
            'date_deadline': '2025-05-10',
        })
        self.assertTrue(exc.name.startswith('GSTEX/'))
        self.assertEqual(exc.activity_ids.user_id, self.env.user)
        exc.action_resolve()
        self.assertEqual(exc.state, 'resolved')
        self.assertEqual(exc.resolved_by_id, self.env.user)
        self.assertFalse(exc.activity_ids)

    def test_ignore_needs_note(self):
        exc = self.Exception.create({'title': 'Old invoice without HSN'})
        with self.assertRaises(UserError):
            exc.action_ignore()
        exc.resolution_note = 'Invoice of 2019, accepted by the auditor.'
        exc.action_ignore()
        self.assertEqual(exc.state, 'ignored')

    def test_sync_findings_lifecycle(self):
        companies = self.default_company.ids
        stats = self.Exception._rn_sync_findings('other', [self._finding('a'), self._finding('b')], companies)
        self.assertEqual(stats['created'], 2)
        exc_a = self.Exception.search([('fingerprint', '=', 'a')])
        exc_b = self.Exception.search([('fingerprint', '=', 'b')])

        # Second scan: 'a' is still there, 'b' is gone.
        stats = self.Exception._rn_sync_findings('other', [self._finding('a', message='still wrong')], companies)
        self.assertEqual((stats['updated'], stats['closed'], stats['created']), (1, 1, 0))
        self.assertEqual(exc_a.seen_count, 2)
        self.assertEqual(exc_a.message, 'still wrong')
        self.assertEqual(exc_b.state, 'resolved')
        self.assertTrue(exc_b.auto_resolved)

        # 'b' comes back: the same record is opened again, no duplicate, and its owner gets a to-do again.
        exc_b.user_id = self.env.user
        self.assertFalse(exc_b.activity_ids)
        stats = self.Exception._rn_sync_findings('other', [self._finding('a'), self._finding('b')], companies)
        self.assertEqual(stats['reopened'], 1)
        self.assertEqual(exc_b.state, 'new')
        self.assertEqual(exc_b.activity_ids.user_id, self.env.user)
        self.assertEqual(self.Exception.search_count([('fingerprint', 'in', ('a', 'b'))]), 2)

        # An ignored problem stays ignored when it is found again.
        exc_a.resolution_note = 'Accepted'
        exc_a.action_ignore()
        self.Exception._rn_sync_findings('other', [self._finding('a'), self._finding('b')], companies)
        self.assertEqual(exc_a.state, 'ignored')

    def test_sync_only_closes_scanned_companies(self):
        other = self.setup_other_company()['company']
        self.Exception._rn_sync_findings('other', [
            self._finding('x'),
            self._finding('y', company_id=other.id),
        ], (self.default_company | other).ids)
        self.Exception._rn_sync_findings('other', [], self.default_company.ids)
        exc_y = self.Exception.sudo().search([('fingerprint', '=', 'y')])
        self.assertEqual(exc_y.state, 'new')

    def test_collect_runs(self):
        result = self.Exception.action_collect()
        self.assertEqual(result['tag'], 'display_notification')

    def test_overdue_filter(self):
        exc = self.Exception.create({'title': 'Late', 'date_deadline': '2000-01-01'})
        self.assertTrue(exc.is_overdue)
        self.assertIn(exc, self.Exception.search([('is_overdue', '=', True)]))
        exc.action_resolve()
        self.assertFalse(exc.is_overdue)
