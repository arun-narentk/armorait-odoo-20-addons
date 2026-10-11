# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Way Bill Manager',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'All e-way bills in one list: expiring, expired, failed, and invoices that need one but have none | ARMORA IT Technologies',
    'description': """
Armora GST E-Way Bill Manager
=============================
Part of the Armora GST Suite for Odoo 20.

* One list of all e-way bills (Odoo has only the form): document, party, vehicle,
  valid-upto date and days left, status
* Status for operations: To Generate, Failed, Active, Expiring Soon, Expired, Cancelled
* Expected validity from distance (1 day per 200 km for normal cargo)
* Invoices without e-way bill: posted goods invoices above the value limit with no
  e-way bill, with "Create E-Way Bill" from the list
* Value limit and "expiring soon" days set on the company
* Daily to-do for the invoice's salesperson when an e-way bill expires within the warning days

Uses Odoo's l10n_in_ewaybill to generate, update and cancel. No second API client.

Developed by ARMORA IT Technologies
Website: https://www.armorait.com/
Email:   info@armorait.com
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'rn_gst_base',
        'l10n_in_ewaybill',
    ],
    'data': [
        'data/ewaybill_manager_cron.xml',
        'views/l10n_in_ewaybill_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 9.00,
    'currency': 'USD',
}
