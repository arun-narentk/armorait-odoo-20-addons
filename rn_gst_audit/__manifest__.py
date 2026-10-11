# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Audit',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST audit run for a period: one checklist across all Armora GST apps, sign-off, Excel audit pack | ARMORA IT Technologies',
    'description': """
Armora GST Audit
================
Part of the Armora GST Suite for Odoo 20.

* Audit run for a period and GSTIN: one checklist built from the installed Armora GST apps
  - invoices with GST validation errors, never validated, or blocked for filing
  - credit note, export and IGST / CGST-SGST errors
  - e-invoices without IRN, invoices without e-way bill
  - GSTR-1 and GSTR-3B filed for each month, GSTR-2B reconciled, ITC ledger locked
  - open GST exceptions, open sales and purchase check findings, bills of blocked suppliers
* Each check: Pass, Warning, Fail, or Not Checked when the app is not installed (never a fail)
* "Open" on a check lists the documents behind it
* Prepared and reviewed sign-off; a signed audit is locked
* Excel audit pack with the checklist and the documents behind each failed check
* Failed checks can be sent to the GST exception inbox

Organises evidence for a review. Does not certify a statutory GST audit.

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
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/rn_gst_audit_security.xml',
        'data/gst_audit_data.xml',
        'views/gst_audit_views.xml',
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
    'price': 12.00,
    'currency': 'USD',
}
