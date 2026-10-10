# -*- coding: utf-8 -*-
{
    'name': 'Armora GST 2B Reconciliation',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTR-2B vs vendor bill matching for Indian GST ITC | ARMORA IT Technologies',
    'description': """
Armora GST 2B Reconciliation
===========================
Part of the Armora GST Suite.

Import GSTR-2B invoice data and match it against posted vendor bills:

* Match on GSTIN, invoice number, date, taxable value, CGST/SGST/IGST/Cess
* Dashboard buckets: Matched, Mismatch, Missing in Odoo, Missing in 2B
* Create vendor bill draft from a 2B line missing in Odoo
* Mark mismatch / ignore / disputed for accountant workflow

Complements Odoo l10n_in GSTR-2B retrieval. This module focuses on
reconciliation UX and exception handling, not replacing GSTN API import.

Depends on armora_gst_base.

Developed by ARMORA IT Technologies
Website: https://www.armorait.com/
Email:   info@armorait.com
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'armora_gst_base',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/gst_2b_security.xml',
        'data/gst_2b_sequence.xml',
        'views/gst_configuration_views.xml',
        'views/gst_gstr2b_views.xml',
        'views/gst_gstr2b_line_views.xml',
        'views/gst_2b_wizard_views.xml',
        'views/gst_2b_menus.xml',
        'security/ir.access.csv',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 25.00,
    'currency': 'USD',
}
