# -*- coding: utf-8 -*-
{
    'name': 'Armora GST ITC',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'ITC ledger with Rule 37, Rule 42 and blocked credit, and the electronic credit ledger | ARMORA IT Technologies',
    'description': """
Armora GST ITC
=============
Part of the Armora GST Suite for Odoo 20.

* Monthly ITC ledger: ITC availed from the month's vendor bills
* ITC type on each bill line: eligible, blocked under section 17(5) or common credit
* Rule 42: common credit reversed in the ratio of exempt to total turnover
* Rule 37: bills unpaid 180 days after their date are reversed with interest, and
  reclaimed in the month the supplier is paid
* Electronic credit ledger: opening, net ITC, credit used in GSTR-3B, closing
* ITC register per bill with paid amount and GSTR-2B status
* Feeds GSTR-3B Tables 4(B)(1), 4(B)(2) and 4(D)(1) when Armora GST GSTR-3B is installed

Complements GSTR-2B / GSTR-3B modules. Does not auto-claim ITC on the GST portal.

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
        'security/rn_gst_itc_security.xml',
        'data/gst_itc_sequence.xml',
        'views/gst_itc_ledger_views.xml',
        'views/account_move_views.xml',
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
    'price': 15.00,
    'currency': 'USD',
}
