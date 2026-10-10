# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Way Bill',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'EWB by IRN tracking and voluntary closure (GSTN Aug 2026) | ARMORA IT Technologies',
    'description': """
Armora GST E-Way Bill
====================
Extends Odoo l10n_in_ewaybill / l10n_in_ewaybill_stock for GSTN Aug 2026:

* EWB lifecycle fields (IRN, status, validity, closure)
* Status values: active, cancelled, discarded, closed (closed proposed by GSTN)
* Voluntary Close E-Way Bill wizard and API service
* Configurable post-closure actions during stabilisation

Does not auto-close on delivery and does not mark delivery done on closure.

Developed by ARMORA IT Technologies
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'armora_gst_einvoice',
        'l10n_in_ewaybill_stock',
        'stock',
    ],
    'data': [
        'wizard/ewaybill_close_wizard_views.xml',
        'views/account_move_views.xml',
        'views/l10n_in_ewaybill_views.xml',
        'views/stock_picking_views.xml',
        'security/ir.access.csv',
    ],
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
