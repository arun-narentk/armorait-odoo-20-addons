# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Exceptions',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'One inbox for GST problems found by the Armora GST apps, with owner, deadline and resolution | ARMORA IT Technologies',
    'description': """
Armora GST Exceptions
=====================
Part of the Armora GST Suite for Odoo 20.

* One inbox for GST problems: invoice validation issues, GSTR-2B mismatches,
  GSTR-1 validation errors, plus problems added by hand
* Each problem has a severity, an owner, a deadline and a resolution note
* Assigning a problem gives the owner a to-do activity
* A daily job pulls new problems from the installed Armora GST apps and
  closes the ones that are no longer found
* Other apps can push their own problems with one method call

Collects problems only. It does not change invoices or bills.

Depends on rn_gst_base. Does not replace Odoo l10n_in / EDI engines.

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
        'security/rn_gst_exception_security.xml',
        'data/gst_exception_data.xml',
        'views/gst_exception_views.xml',
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
