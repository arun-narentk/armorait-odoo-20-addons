# -*- coding: utf-8 -*-
import base64
import os
import time
from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import ChromeBrowser, HttpCase

from .common import RnGstFilingTestCommon


SCREENSHOTS_DIR = Path(__file__).resolve().parents[1] / 'static' / 'description' / 'screenshots'


@tagged('post_install', '-at_install', 'rn_screenshots')
class TestRnGstFilingScreenshots(HttpCase, RnGstFilingTestCommon):
    """Capture Apps Store screenshots (run with ARMORA_CAPTURE_SCREENSHOTS=1)."""

    def setUp(self):
        super().setUp()
        if not os.environ.get('ARMORA_CAPTURE_SCREENSHOTS'):
            self.skipTest('Set ARMORA_CAPTURE_SCREENSHOTS=1 to capture Apps Store screenshots')

    def _save_png(self, browser, filename):
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        future = browser._websocket_send('Page.captureScreenshot', with_future=True)
        result = future.result(timeout=30)
        data = base64.b64decode(result['data'])
        path = SCREENSHOTS_DIR / filename
        path.write_bytes(data)
        self.assertGreater(path.stat().st_size, 5000, 'Screenshot too small: %s' % path)
        return path

    def _open(self, browser, url_path, ready='.o_action_manager, .o_list_view, .o_form_view'):
        browser.navigate_to(self.base_url() + url_path, wait_stop=True)
        if ready:
            self.assertTrue(browser._wait_ready(ready), 'Page not ready: %s' % url_path)
        time.sleep(2)

    def _click_tab(self, browser, label):
        browser._websocket_send('Runtime.evaluate', params={
            'expression': """
                (() => {
                    const tabs = [...document.querySelectorAll('.nav-link, .o_notebook_headers a')];
                    const tab = tabs.find(t => (t.textContent || '').trim().includes(%s));
                    if (tab) { tab.click(); return true; }
                    return false;
                })()
            """ % repr(label),
            'returnByValue': True,
        })
        time.sleep(1.5)

    def test_capture_apps_store_screenshots(self):
        filing = self.env['rn.gst.filing'].search([
            ('company_id', '=', self.default_company.id),
            ('return_period', '=', '04'),
            ('financial_year', '=', '2025-26'),
        ], limit=1)
        if not filing:
            filing = self._create_gst_filing('04')
            filing.action_load_data()
            filing.action_validate()
        filing_id = filing.id

        act_filing = self.env.ref('rn_gst_filing.action_rn_gst_filing').id
        act_validation = self.env.ref('rn_gst_filing.action_rn_gst_rule_validation').id
        act_template = self.env.ref('rn_gst_filing.action_rn_gst_excel_template').id

        shots = [
            ('01_dashboard.png', f'/web#action={act_filing}&model=rn.gst.filing&view_type=list', None),
            ('02_gst_filing_form.png', f'/web#id={filing_id}&model=rn.gst.filing&view_type=form', None),
            ('03_gst_validation.png', f'/web#action={act_validation}&model=rn.gst.validation.result&view_type=list', None),
            ('04_gst_lines.png', f'/web#id={filing_id}&model=rn.gst.filing&view_type=form', 'GST Lines'),
            ('05_gst_excel_generation.png', f'/web#id={filing_id}&model=rn.gst.filing&view_type=form', 'GST Upload File'),
            ('06_gst_template_configuration.png', f'/web#action={act_template}&model=rn.gst.excel.template&view_type=list', None),
            ('07_gst_filing_summary.png', f'/web#id={filing_id}&model=rn.gst.filing&view_type=form', 'Summary'),
        ]

        browser = ChromeBrowser(self, headless=True)
        try:
            self.authenticate('admin', 'admin', browser=browser)
            self.cr.flush()
            self.cr.clear()
            for filename, url_path, tab in shots:
                self._open(browser, url_path)
                if tab:
                    self._click_tab(browser, tab)
                    time.sleep(1)
                path = self._save_png(browser, filename)
                self._logger.info('Saved screenshot %s (%s bytes)', path, path.stat().st_size)
        finally:
            browser.stop()
            self._wait_remaining_requests()
