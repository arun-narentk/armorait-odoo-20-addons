# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Reverse Charge',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Reverse charge GST tracking and checks for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Reverse Charge
========================
Part of the Armora GST Suite for Odoo 20.

* Identify reverse-charge liable purchases/services
* Check tax configuration consistency for RCM
* Accountant views for RCM liability review

Uses Odoo l10n_in reverse charge tax flags. Does not invent RCM legal rules.

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
        'security/armora_gst_rcm_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
