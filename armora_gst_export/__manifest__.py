# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Export',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Export and SEZ GST document checks for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Export
================
Part of the Armora GST Suite for Odoo 20.

* Validate export invoice completeness (shipping bill, port, etc.)
* Support SEZ / deemed export review fields already on Indian invoices
* Highlight missing export GST information before filing

Builds on l10n_in export fields. Does not submit documents to customs/GSTN.

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
        'security/armora_gst_export_security.xml',
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
