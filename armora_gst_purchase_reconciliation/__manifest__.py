# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Purchase Reconciliation',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Reconcile purchase invoices and GST ITC documents for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Purchase Reconciliation
=================================
Part of the Armora GST Suite for Odoo 20.

* Match vendor bills to GST purchase documents
* Highlight missing, mismatched, or duplicate purchase GST data
* Accountant-friendly reconciliation status and differences

Complements GSTR-2B workflows; does not replace armora_gst_2b_reconciliation.

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
        'security/armora_gst_purchase_reconciliation_security.xml',
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
