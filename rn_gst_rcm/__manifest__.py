# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Reverse Charge',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Reverse charge rules, bill checks, self-invoices and time of supply for Indian GST | ARMORA IT Technologies',
    'description': """
Armora GST Reverse Charge
========================
Part of the Armora GST Suite for Odoo 20.

* RCM rules: notified supplies (section 9(3)), supplies from unregistered persons
  (section 9(4)) and import of services, linked to products, categories or accounts
* Vendor bill check: warns when a line needs a reverse charge tax and applies it
* Self-invoice for reverse charge purchases from unregistered suppliers, with its
  own numbering, PDF and 30-day limit
* Time of supply: payment date or 61st day after the supplier invoice for services
* RCM register with tax, time-of-supply month, payment and self-invoice status

Uses Odoo l10n_in reverse charge taxes. The rules ship without tax rates: pick the
taxes and check each notification's conditions.

Depends on rn_gst_base. Does not replace Odoo l10n_in / EDI engines.

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
        'security/rn_gst_rcm_security.xml',
        'data/gst_rcm_data.xml',
        'report/self_invoice_report.xml',
        'views/gst_rcm_rule_views.xml',
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
    'price': 12.00,
    'currency': 'USD',
}
