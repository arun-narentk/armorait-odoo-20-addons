# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Analytics',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST analysis from posted entries: output and input GST by month, head, GSTR section, customer and supplier | ARMORA IT Technologies',
    'description': """
Armora GST Analytics
====================
Part of the Armora GST Suite for Odoo 20.

* Live report of taxable value and GST from posted journal items, read from the Indian
  GST tax tags (no copy of the data, always up to date)
* Outward (sales) and inward (purchases) GST by month, IGST / CGST / SGST / Cess,
  GSTR-1 section, journal, customer or supplier
* Pivot, graph and list views, with ready filters for this month, last month and this
  financial year, and Excel export from the pivot
* Month-on-month view of output GST against input GST

Read-only analysis; does not change accounting entries.

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
    ],
    'data': [
        'views/gst_analytics_views.xml',
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
