# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Rules',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Versioned GST rules, validation engine and API audit | ARMORA IT Technologies',
    'description': """
Armora GST Rules
===============
Shared rule versioning and pre-submission validation for the Armora GST Suite.

* armora.gst.rule with effective dates and JSON configuration
* armora.gst.validation reusable validation service
* armora.gst.api.audit request/response audit (no secrets)
* Company GST API configuration (sandbox / production)

Does not replace Odoo l10n_in EDI engines.

Developed by ARMORA IT Technologies
Website: https://www.armorait.com/
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'armora_gst_base',
    ],
    'data': [
        'data/gst_rules_data.xml',
        'views/gst_rule_views.xml',
        'views/gst_api_audit_views.xml',
        'views/gst_configuration_views.xml',
        'views/gst_menus.xml',
        'security/ir.access.csv',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
