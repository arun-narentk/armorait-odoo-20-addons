# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Invoice Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Invoice-level GST compliance scoring for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Invoice Compliance
============================
Part of the Armora GST Suite for Odoo 20.

* Score invoices against shared GST compliance checks
* Show blocking vs advisory issues clearly
* Bridge invoice validation results into compliance dashboards

Extends armora_gst_invoice_validator with compliance-oriented views.

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
        'armora_gst_invoice_validator',
    ],
    'data': [
        'security/armora_gst_invoice_compliance_security.xml',
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
