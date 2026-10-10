# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Exception Center',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Central GST exception inbox for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Exception Center
==========================
Part of the Armora GST Suite for Odoo 20.

* Aggregate GST warnings/errors from Armora GST modules
* Assign and track exception resolution
* Provide a single accountant inbox for GST blockers

Foundation exception center. Downstream modules can post issues into it later.

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
        'security/armora_gst_exception_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 9.00,
    'currency': 'USD',
}
