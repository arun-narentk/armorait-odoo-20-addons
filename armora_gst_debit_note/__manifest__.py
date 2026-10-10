# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Debit Note',
    'version': '20.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST debit note compliance and control for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Debit Note
====================
Part of the Armora GST Suite for Odoo 20.

* GST debit-note detection via Odoo debit_origin_id (not out_refund)
* Reason master and validation result shells
* Review wizard shell for additional taxable value / tax checks

Does NOT:

* Replace account.move or account_debit_note
* Clone credit-note reduction validation as debit-note rules
* Compute taxes or post accounting entries
* Call E-Invoice / E-Way Bill APIs
* Depend on armora_gst_credit_note

Odoo remains responsible for tax calculation and posting.
Debit notes increase GST liability; credit notes decrease it.

Depends on armora_gst_base and account_debit_note.

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
        'account_debit_note',
    ],
    'data': [
        'security/armora_gst_debit_note_security.xml',
        'data/gst_debit_note_data.xml',
        'views/gst_debit_note_reason_views.xml',
        'views/gst_debit_note_validation_views.xml',
        'views/gst_debit_note_wizard_views.xml',
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
