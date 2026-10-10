# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Multi-GSTIN',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Multi-GSTIN operations on top of Armora GST registrations for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Multi-GSTIN
=====================
Part of the Armora GST Suite for Odoo 20.

* Operate across multiple GST registrations per company
* Help select/filter documents by GSTIN / state registration
* Extend armora.gst.registration for operational use cases

Depends on armora.gst.registration from armora_gst_base.

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
        'security/armora_gst_multi_gstin_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
