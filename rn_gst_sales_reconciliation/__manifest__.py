# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Sales Reconciliation',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Monthly check of sales books against output GST in the ledger, invoice numbering and the filed GSTR-1 | ARMORA IT Technologies',
    'description': """
Armora GST Sales Reconciliation
===============================
Part of the Armora GST Suite for Odoo 20.

Run it for a month of a GSTIN:

* Output GST in the ledger against GST on sales invoices: journal entries that post
  to output GST accounts (tax that GSTR-1 will not show)
* Invoice numbering: gaps in the sales document series, and cancelled invoices to
  report in the GSTR-1 document summary
* Books against the GSTR-1 already marked filed in Armora GST Filing: invoices added,
  changed or cancelled after filing (to amend in a later GSTR-1)
* Totals: taxable value and tax in books, in the ledger and in the filed return
* Each finding can be marked Reviewed or Ignored with a note

Does not prepare GSTR-1; it checks the books against what was filed.

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
        'security/rn_gst_sales_recon_security.xml',
        'data/gst_sales_recon_data.xml',
        'views/gst_sales_recon_views.xml',
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
