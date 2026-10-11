# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Calendar',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST return due dates per GSTIN: GSTR-1, GSTR-3B, PMT-06, CMP-08, GSTR-4, GSTR-9, with extensions and reminders | ARMORA IT Technologies',
    'description': """
Armora GST Calendar
===================
Part of the Armora GST Suite for Odoo 20.

* Due-date rules per return, kept as data with effective dates, not fixed in code:
  GSTR-1 (11th, or 13th for QRMP), GSTR-3B (20th, or 22nd / 24th for QRMP by state),
  PMT-06 (25th), CMP-08 (18th), GSTR-4 (30 April), GSTR-9 and GSTR-9C (31 December), GSTR-6 (13th)
* Monthly or quarterly (QRMP) filing set on each GST registration
* Generate the whole year's returns for one or more GSTINs in one click
* Due-date extensions by notification, for all states or some states
* Calendar, list and kanban of pending, overdue and filed returns, with days late
* Reminder activity to the person responsible a set number of days before the due date
* Marks a return filed when the matching Armora GSTR-1, GSTR-3B or GSTR-9 record is filed

Does not file returns or connect to the GST portal.

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
        'mail',
    ],
    'data': [
        'security/rn_gst_calendar_security.xml',
        'data/gst_return_type_data.xml',
        'data/gst_calendar_cron.xml',
        'views/gst_obligation_views.xml',
        'views/gst_return_type_views.xml',
        'views/gst_registration_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/gst_obligation_generate_wizard_views.xml',
        'views/menus.xml',
        'security/ir.access.csv',
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
