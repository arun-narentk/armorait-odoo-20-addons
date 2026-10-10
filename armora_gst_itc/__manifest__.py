# -*- coding: utf-8 -*-
{
    'name': 'Armora GST ITC',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Input Tax Credit tracking and review for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST ITC
=============
Part of the Armora GST Suite for Odoo 20.

* Track ITC eligible, ineligible, and reversed amounts
* Support period review of purchase-side GST credit
* Foundation for ITC utilization and reconciliation extensions

Complements GSTR-2B / GSTR-3B modules. Does not auto-claim ITC on the GST portal.

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
        'security/armora_gst_itc_security.xml',
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
