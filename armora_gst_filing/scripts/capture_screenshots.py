#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture Armora GST Filing screenshots via Selenium + Odoo JSON-RPC auth."""
import json
import sys
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = 'http://127.0.0.1:9204'
DB = 'armora18_gst_demo'
LOGIN = 'admin'
PASSWORD = 'admin'
OUT = Path(__file__).resolve().parents[1] / 'static' / 'description' / 'screenshots'
FILING_ID = 3

SHOTS = [
    ('01_dashboard.png', f'{BASE}/web#action=305&model=armora.gst.filing&view_type=list', 'GST Returns list'),
    ('02_gst_filing_form.png', f'{BASE}/web#id={FILING_ID}&model=armora.gst.filing&view_type=form', 'Filing form'),
    ('03_gst_validation.png', f'{BASE}/web#action=304&model=armora.gst.validation.result&view_type=list', 'Validation'),
    ('04_gst_lines.png', f'{BASE}/web#id={FILING_ID}&model=armora.gst.filing&view_type=form', 'GST Lines tab', 'lines'),
    ('05_gst_excel_generation.png', f'{BASE}/web#id={FILING_ID}&model=armora.gst.filing&view_type=form', 'Excel tab', 'excel'),
    ('06_gst_template_configuration.png', f'{BASE}/web#action=303&model=armora.gst.excel.template&view_type=list', 'Templates'),
    ('07_gst_filing_summary.png', f'{BASE}/web#id={FILING_ID}&model=armora.gst.filing&view_type=form', 'Summary tab', 'summary'),
]


def authenticate():
    session = requests.Session()
    payload = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {'db': DB, 'login': LOGIN, 'password': PASSWORD},
        'id': 1,
    }
    resp = session.post(f'{BASE}/web/session/authenticate', json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get('error'):
        raise RuntimeError('Auth failed: %s' % data['error'])
    return session


def build_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1400,900')
    options.add_argument('--force-device-scale-factor=1')
    options.add_argument('--hide-scrollbars')
    return webdriver.Chrome(options=options)


def inject_cookies(driver, session):
    driver.get(BASE)
    time.sleep(0.5)
    for cookie in session.cookies:
        try:
            driver.add_cookie({
                'name': cookie.name,
                'value': cookie.value,
                'path': '/',
            })
        except Exception:
            pass


def wait_odoo(driver, timeout=40):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                '.o_action_manager, .o_list_view, .o_form_view, .o_home_menu',
            ))
        )
    except Exception:
        debug = OUT / '_debug_timeout.png'
        driver.save_screenshot(str(debug))
        raise
    time.sleep(2.5)


def click_tab(driver, tab_key):
    labels = {
        'lines': 'GST Lines',
        'validation': 'Validation',
        'excel': 'GST Upload File',
        'summary': 'Summary',
    }
    label = labels.get(tab_key, tab_key)
    tabs = driver.find_elements(By.CSS_SELECTOR, '.nav-link, .o_notebook_headers .nav-item a')
    for tab in tabs:
        if label.lower() in (tab.text or '').lower():
            tab.click()
            time.sleep(1.5)
            return
    # fallback xpath
    xpath = f"//a[contains(normalize-space(.), '{label}')]"
    el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    el.click()
    time.sleep(1.5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    session = authenticate()
    driver = build_driver()
    try:
        inject_cookies(driver, session)
        driver.get(f'{BASE}/web')
        wait_odoo(driver)
        for item in SHOTS:
            filename = item[0]
            url = item[1]
            tab = item[3] if len(item) > 3 else None
            print('Capture', filename, '...')
            driver.get(url)
            wait_odoo(driver)
            if tab:
                click_tab(driver, tab)
            path = OUT / filename
            driver.save_screenshot(str(path))
            if not path.exists() or path.stat().st_size < 5000:
                print('WARN: small screenshot', path, path.stat().st_size if path.exists() else 0)
            else:
                print('OK', path, path.stat().st_size)
    finally:
        driver.quit()
    print('Done. Files in', OUT)


if __name__ == '__main__':
    main()
