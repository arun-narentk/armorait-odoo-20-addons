# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRnGstAudit(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reviewer_group = cls.env.ref('rn_gst_audit.group_rn_gst_audit_reviewer')
        cls.env.user.group_ids = [(4, reviewer_group.id)]
        if 'rn_gst_block_post_on_error' in cls.default_company._fields:
            cls.default_company.rn_gst_block_post_on_error = False
        cls.reviewer = cls.env['res.users'].create({
            'name': 'GST Reviewer', 'login': 'gst_audit_reviewer',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, reviewer_group.id])],
            'company_id': cls.default_company.id, 'company_ids': [(6, 0, cls.default_company.ids)],
        })

    def _audit(self):
        audit = self.env['rn.gst.audit'].create({'date_from': '2025-04-01', 'date_to': '2025-04-30'})
        audit.action_run()
        return audit

    def _check(self, audit, code):
        return audit.check_ids.filtered(lambda c: c.code == code)

    def test_checklist(self):
        move = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-04-10')
        move.action_post()
        audit = self._audit()
        self.assertEqual(audit.state, 'checked')
        self.assertTrue(audit.check_ids)
        self.assertEqual(audit.prepared_by_id, self.env.user)
        self.assertEqual(audit.pass_count + audit.warning_count + audit.fail_count + audit.unknown_count,
                         len(audit.check_ids))
        gstr1 = self._check(audit, 'gstr1_filed')
        if 'rn.gst.filing' in self.env:
            self.assertEqual(gstr1.result, 'fail')
            self.assertIn('2025-26/04', gstr1.message)
        else:
            self.assertEqual(gstr1.result, 'unknown')
        if 'rn_gst_validation_status' in self.env['account.move']._fields:
            move.rn_gst_validation_status = 'pending'
            audit.action_run()
            not_validated = self._check(audit, 'not_validated')
            self.assertEqual(not_validated.result, 'warning')
            self.assertIn(move, not_validated._rn_records())
            action = not_validated.action_open()
            self.assertEqual(action['res_model'], 'account.move')

    def test_validator_errors_fail(self):
        if 'rn_gst_error_count' not in self.env['account.move']._fields:
            self.skipTest('Armora GST Invoice Validator is not installed.')
        move = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], taxes=self.sgst_sale_18,
                                 invoice_date='2025-04-10')
        move.invoice_line_ids.l10n_in_hsn_code = False
        move.action_post()
        move.action_rn_gst_validate()
        check = self._check(self._audit(), 'validator_errors')
        self.assertEqual(check.result, 'fail')
        self.assertEqual(check.count, 1)

    def test_sign_off_and_lock(self):
        audit = self._audit()
        self.assertTrue(audit.fail_count)
        with self.assertRaises(UserError):
            audit.with_user(self.reviewer).action_sign()
        audit.review_note = 'Returns for April filed on the portal, Odoo records to be updated.'
        with self.assertRaises(UserError):
            audit.action_sign()  # the preparer cannot review their own audit
        audit.with_user(self.reviewer).action_sign()
        self.assertEqual(audit.state, 'signed')
        self.assertEqual(audit.reviewed_by_id, self.reviewer)
        with self.assertRaises(UserError):
            audit.date_to = '2025-05-31'
        with self.assertRaises(UserError):
            audit.action_run()
        audit.action_reopen()
        audit.action_run()
        self.assertFalse(audit.reviewed_by_id)

    def test_audit_pack(self):
        audit = self._audit()
        audit.action_export_pack()
        self.assertTrue(audit.pack_id.name.endswith('.xlsx'))
        self.assertTrue(audit.pack_id.raw.content.startswith(b'PK'))

    def test_send_to_exceptions(self):
        if 'rn.gst.exception' not in self.env:
            self.skipTest('Armora GST Exceptions is not installed.')
        audit = self._audit()
        audit.action_send_to_exceptions()
        Exception_ = self.env['rn.gst.exception'].sudo()
        domain = [('fingerprint', '=like', 'audit:%s:%%' % audit.id)]
        count = Exception_.search_count(domain)
        self.assertEqual(count, audit.fail_count + audit.warning_count)
        other = Exception_.create({'title': 'Manual problem', 'source': 'other', 'fingerprint': 'manual:1'})
        audit.action_send_to_exceptions()
        self.assertEqual(Exception_.search_count(domain), count)
        self.assertEqual(other.state, 'new')
