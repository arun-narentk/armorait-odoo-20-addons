# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Base',
    'version': '20.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'Foundation framework for the Armora Indian GST ecosystem on Odoo 20',
    'description': """
Armora GST Base for Odoo 20
==========================
Reusable foundation layer for the Armora Indian GST ecosystem.

Provides shared infrastructure used by other Armora GST modules:

* GST registration configuration (multi-GSTIN per company)
* GSTIN structural validation helpers
* Indian financial year and return-period helpers
* Decimal-safe monetary helpers
* Shared Armora GST security groups and root menu
* Company-level GST settings used across the suite

This module does NOT provide:

* GSTR-1 / GSTR-3B / GSTR-2B filing workflows
* E-Invoice or E-Way Bill submission
* GST Portal API integration
* Offline Tool Excel generation

Those capabilities belong in separate Armora GST modules that depend on this base.

Depends on Indian Accounting (l10n_in). Complements Odoo localization; does not
replace Odoo e-Invoice or E-Way Bill engines.

Developed by ARMORA IT Technologies
Website: https://www.armorait.com/
Email:   info@armorait.com
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'account',
        'l10n_in',
    ],
    'data': [
        'security/armora_gst_security.xml',
        'views/gst_registration_views.xml',
        'views/gst_configuration_views.xml',
        'views/gst_menus.xml',
        'security/ir.access.csv',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
