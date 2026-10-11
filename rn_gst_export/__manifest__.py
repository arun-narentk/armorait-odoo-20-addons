# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Exports',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Export and SEZ invoices: LUT register, Rule 96A time limits, shipping bill, payment realisation, IGST refund readiness | ARMORA IT Technologies',
    'description': """
Armora GST Exports
==================
Part of the Armora GST Suite for Odoo 20.

* LUT register: ARN, financial year and dates per GSTIN, with the export invoices it covers
* Export type of each invoice: under LUT (no IGST) or with IGST paid, read from Odoo's LUT taxes
* Checks on export and SEZ invoices:
  - LUT exports need an LUT in force on the invoice date
  - Rule 96A: goods under LUT must leave India within 3 months of the invoice
  - Rule 96A: services under LUT must be paid in foreign exchange within 1 year
  - goods exports need the shipping bill number, date and port
  - an invoice must not mix LUT and IGST-paid lines
* Payment realisation from the invoice's payments, with the bank realisation (e-BRC / FIRC) number
* IGST refund readiness for exports with IGST paid (shipping bill, port and IGST present)
* Export register with filters for every problem

Uses the l10n_in export fields. Does not file shipping bills or refund claims.

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
        'security/rn_gst_export_security.xml',
        'data/export_cron.xml',
        'views/gst_lut_views.xml',
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
