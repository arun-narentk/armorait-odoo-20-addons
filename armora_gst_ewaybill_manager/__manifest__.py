# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Way Bill Manager',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Manage and monitor E-Way Bill status for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST E-Way Bill Manager
============================
Part of the Armora GST Suite for Odoo 20.

* Track E-Way Bill generation and validity
* Highlight pending, expired, or failed E-Way Bills
* Operational views for logistics and accounts teams

Complements Odoo l10n_in_ewaybill and existing armora_gst_ewaybill extensions.

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
        'security/armora_gst_ewaybill_manager_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': False,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
