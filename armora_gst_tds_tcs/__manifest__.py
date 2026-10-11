# -*- coding: utf-8 -*-
{
    'name': 'Armora GST TDS/TCS',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST TDS and TCS credits from deductors and e-commerce operators, with GSTR-2X matching | ARMORA IT Technologies',
    'description': """
Armora GST TDS and TCS
======================
Part of the Armora GST Suite for Odoo 20.

For suppliers whose customers deduct GST TDS (section 51) and for sellers on
e-commerce marketplaces that collect GST TCS (section 52):

* Mark customers as GST TDS deductors or e-commerce operators
* Monthly expected credits from posted invoices: TDS on invoices above the
  threshold, TCS on the net value of supplies, split into CGST and SGST or IGST
* Import the GSTR-2X credits from the GST Portal and match them per deductor
* Accept or reject credits; accepted credits can be booked against the
  customer's receivable

Does not file GSTR-7 or GSTR-8 for deductors and operators.

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
        'mail',
    ],
    'data': [
        'security/armora_gst_tds_tcs_security.xml',
        'data/gst_tds_tcs_sequence.xml',
        'views/gst_tds_tcs_views.xml',
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
