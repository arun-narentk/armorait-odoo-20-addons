# -*- coding: utf-8 -*-
{
    'name': 'Armora GST GSTR-3B',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTR-3B interest, liability breakup and versioned ITC utilization | ARMORA IT Technologies',
    'description': """
Armora GST GSTR-3B
=================
Implements GSTN GSTR-3B enhancements from January 2026 onward:

* Fill Tables 3.1, 3.2, 4 and 5 from posted invoices and bills, using the GSTR
  section Odoo's Indian localization sets on every invoice line
* Interest calculator using minimum Electronic Cash Ledger balance (Rule 88B(1))
* Tax liability breakup for previous-period supplies reported later
* Configurable / versioned ITC utilization engine (not a hard-coded single rule)

System-computed interest is a minimum; self-assessed interest may be higher only.

Developed by ARMORA IT Technologies
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'armora_gst_rules',
        'armora_gst_filing',
        'mail',
    ],
    'data': [
        'report/gstr3b_summary_report.xml',
        'views/gst_3b_views.xml',
        'views/gst_filing_views.xml',
        'views/gst_menus.xml',
        'security/ir.access.csv',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 15.00,
    'currency': 'USD',
}
