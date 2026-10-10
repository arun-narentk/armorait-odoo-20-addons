# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Audit',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST audit trail and review pack helpers for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Audit
===============
Part of the Armora GST Suite for Odoo 20.

* Collect GST-relevant audit evidence for a period
* Summarize validation exceptions and configuration changes
* Support internal / external GST review workflows

Does not claim statutory GST audit certification.

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
        'security/armora_gst_audit_security.xml',
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
