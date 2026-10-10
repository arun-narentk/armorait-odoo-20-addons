# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Invoice',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTN Aug 2026 e-Invoice validations on top of l10n_in_edi | ARMORA IT Technologies',
    'description': """
Armora GST E-Invoice
===================
Extends Odoo l10n_in_edi for GSTN advisory changes effective 1 August 2026:

* Conditional Ship-to GSTIN when ShipDtls + EWB required
* GSTIN / state / PIN validations
* Bill-to vs Ship-to distinct GSTIN
* ExpShipDtls.Gstin for EWB by IRN
* URP support
* B2B/SEZ ship-to lock after IRN

Does not replace IRN generation. Uses Odoo EDI + Armora validation rules.

Developed by ARMORA IT Technologies
    """,
    'author': 'ARMORA IT Technologies',
    'maintainer': 'ARMORA IT Technologies',
    'website': 'https://www.armorait.com/',
    'support': 'info@armorait.com',
    'depends': [
        'armora_gst_rules',
        'l10n_in_edi',
        'l10n_in_ewaybill_irn',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 12.00,
    'currency': 'USD',
}
