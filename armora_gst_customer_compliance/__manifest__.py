# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Customer Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Customer GST compliance monitoring for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Customer Compliance
=============================
Part of the Armora GST Suite for Odoo 20.

* Monitor customer GSTIN completeness and treatment setup
* Highlight customers with repeated sales GST issues
* Support outward-supply compliance reviews

Partner-centric compliance for customers/receivables.

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
        'security/armora_gst_customer_compliance_security.xml',
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
