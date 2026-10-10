# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Calendar',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST return and compliance calendar for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Calendar
==================
Part of the Armora GST Suite for Odoo 20.

* Track GST return due dates by period
* Company-specific filing calendar reminders
* Overview of upcoming GST compliance deadlines

Calendar helpers only. Does not file returns or connect to GST Portal.

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
        'security/armora_gst_calendar_security.xml',
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
