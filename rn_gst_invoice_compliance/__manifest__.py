# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Invoice Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'One GST readiness status per invoice: blocked, needs review, ready or approved, with reviewer sign-off | ARMORA IT Technologies',
    'description': """
Armora GST Invoice Compliance
=============================
Part of the Armora GST Suite for Odoo 20.

* One GST readiness status on every invoice and bill: Not Checked, Blocked,
  Needs Review, Ready or Approved, with the reasons listed
* Built from the Armora GST Invoice Validator result, and when installed:
  the credit note checks, the IGST / CGST-SGST check of Multi-GSTIN, and the
  e-invoice IRN status of Odoo's Indian e-invoicing
* Reviewer sign-off: approve warnings with a note; only a compliance manager can
  approve blocked invoices. A new problem after approval sends the invoice back to review
* Compliance board: list, kanban and month-by-status pivot, with "Validate" and
  "Approve" on many invoices at once

Uses the validator's findings; it does not add a second posting check.

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
        'rn_gst_invoice_validator',
    ],
    'data': [
        'security/rn_gst_invoice_compliance_security.xml',
        'views/account_move_views.xml',
        'wizard/gst_compliance_review_wizard_views.xml',
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
