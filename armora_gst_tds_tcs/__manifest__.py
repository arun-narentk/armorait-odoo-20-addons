# -*- coding: utf-8 -*-
{
    'name': 'Armora GST TDS/TCS',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST TDS and TCS tracking helpers for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST TDS/TCS
=================
Part of the Armora GST Suite for Odoo 20.

* Identify GST TDS/TCS relevant documents
* Track TDS/TCS amounts for review
* Support accountant checks around GST withholding scenarios

Does not replace Odoo Indian withholding modules. Complements the TDS/TCS features of Odoo l10n_in.

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
        'security/armora_gst_tds_tcs_security.xml',
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
