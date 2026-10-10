# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Invoice Monitor',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Monitor e-Invoice IRN status and exceptions for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST E-Invoice Monitor
===========================
Part of the Armora GST Suite for Odoo 20.

* Track IRN generation status on Indian GST invoices
* Surface pending, failed, and cancelled e-Invoice cases
* Provide accountant views without replacing Odoo EDI engines

Complements Odoo l10n_in_edi and existing armora_gst_einvoice extensions.

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
        'security/armora_gst_einvoice_monitor_security.xml',
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
