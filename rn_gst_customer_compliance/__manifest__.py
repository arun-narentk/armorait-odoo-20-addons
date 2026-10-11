# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Customer Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST profile per customer: GSTIN and treatment set-up, B2B reported as B2C, invoice and e-invoice problems, risk score | ARMORA IT Technologies',
    'description': """
Armora GST Customer Compliance
==============================
Part of the Armora GST Suite for Odoo 20.

* One GST profile per customer and company, refreshed from the customer's data:
  - GSTIN structure, and the GSTIN check status when Armora GSTIN Verification is installed
  - GST treatment against the GSTIN: a registered customer set up as unregistered or consumer
    makes B2B invoices show as B2C in GSTR-1, and the customer loses ITC
  - state of the GSTIN against the state on the address
  - invoices of the last 12 months, invoices with GST validation errors, wrong IGST / CGST-SGST
  - credit notes with GST errors, and credit notes above 20% of sales
  - e-invoices failed or pending for more than 7 days
* Findings, score out of 100 and risk, with a warning on the customer invoice for high risk
* Weekly refresh; never blocks sales

Developed by ARMORA IT Technologies
Website: https://www.armorait.com/
Email:   info@armorait.com
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'rn_gst_base',
        'mail',
    ],
    'data': [
        'security/rn_gst_customer_compliance_security.xml',
        'data/customer_compliance_cron.xml',
        'views/gst_customer_profile_views.xml',
        'views/account_move_views.xml',
        'views/menus.xml',
        'security/ir.access.csv',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 9.00,
    'currency': 'USD',
}
