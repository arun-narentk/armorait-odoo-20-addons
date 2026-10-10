# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Rate Manager',
    'version': '20.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST rate configuration and change control for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Rate Manager
======================
Part of the Armora GST Suite for Odoo 20.

* Logical GST rate master with effective dating and component rates
* Mapping fields to existing Odoo account.tax records
* Overlap prevention for active rate versions
* Conflict detection and change-control workflow shells
* Controlled bulk update wizard shell

Does NOT:

* Replace Odoo tax computation or invoice totals
* Own HSN/SAC classification (see armora_gst_hsn_validator)
* File GST returns or submit E-Invoice / E-Way Bill
* Depend on armora_gst_invoice_validator (that module may consume lookups later)

Odoo account.tax remains the calculation source of truth.

Depends on armora_gst_base. Complements Odoo l10n_in.

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
        'security/armora_gst_rate_manager_security.xml',
        'data/gst_rate_data.xml',
        'views/gst_rate_views.xml',
        'views/gst_rate_change_views.xml',
        'views/gst_rate_history_views.xml',
        'views/gst_rate_conflict_views.xml',
        'views/gst_rate_wizard_views.xml',
        'views/menus.xml',
        'security/ir.access.csv',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 9.00,
    'currency': 'USD',
}
