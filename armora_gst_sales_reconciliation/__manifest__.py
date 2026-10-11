# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Sales Reconciliation',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Reconcile sales invoices against GST outward supply data for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Sales Reconciliation
==============================
Part of the Armora GST Suite for Odoo 20.

* Match customer invoices to outward GST supply records
* Flag missing invoices, tax mismatches, and duplicates
* Support period-based sales reconciliation reviews

Complements GSTR-1 filing workflows in armora_gst_filing.

Depends on armora_gst_base. Does not replace Odoo l10n_in / EDI engines.

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
    'data': [
        'security/armora_gst_sales_reconciliation_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': False,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
