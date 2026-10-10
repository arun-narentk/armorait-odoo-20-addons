# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Analytics',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST analytics and KPI views for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Analytics
===================
Part of the Armora GST Suite for Odoo 20.

* Period KPIs for outward/inward GST tax
* Exception and compliance trend summaries
* Read-only analytical views for management review

Analytics layer only. Does not modify accounting entries.

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
        'security/armora_gst_analytics_security.xml',
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
}
