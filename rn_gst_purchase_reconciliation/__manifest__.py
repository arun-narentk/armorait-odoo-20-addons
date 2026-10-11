# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Purchase Reconciliation',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Check vendor bills of a period against purchase orders and receipts before GSTR-2B and ITC | ARMORA IT Technologies',
    'description': """
Armora GST Purchase Reconciliation
==================================
Part of the Armora GST Suite for Odoo 20.

Run it for a month (or any period) to check every posted vendor bill:

* Same supplier invoice number entered twice in the financial year (duplicate ITC)
* Bill without the supplier invoice number (GSTR-2B matching needs it)
* Supplier GSTIN changed since the bill was posted
* More quantity billed than received on the purchase order
* Unit price above the purchase order price (beyond the tolerance)
* GST rate on the bill different from the purchase order
* HSN code on the bill different from the product's HSN
* Goods bills not linked to any purchase order

Each finding can be marked Reviewed or Ignored with a note. Different from GSTR-2B
reconciliation: this compares the bill with your own purchase documents.

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
        'purchase',
        'mail',
    ],
    'data': [
        'security/rn_gst_purchase_recon_security.xml',
        'data/gst_purchase_recon_data.xml',
        'views/gst_purchase_recon_views.xml',
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
