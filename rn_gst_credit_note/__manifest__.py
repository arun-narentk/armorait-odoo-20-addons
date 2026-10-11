# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Credit Notes',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST checks on credit notes: original invoice, section 34 time limit, amount left to credit, same tax rates | ARMORA IT Technologies',
    'description': """
Armora GST Credit Notes
=======================
Part of the Armora GST Suite for Odoo 20.

Checks every customer and vendor credit note before it reaches GSTR-1:

* Reason for the credit note (sales return, price reduction, deficiency, discount...)
  picked when the credit note is made from the invoice
* Original invoice linked, posted, for the same customer and GSTIN
* Section 34(2) time limit: GST can be reduced only up to 30 November after the end of
  the financial year of the original invoice
* Total credited on an invoice cannot go above the invoice's taxable value
* Same GST rates, same IGST or CGST/SGST and same place of supply as the original invoice
* Financial credit notes (discounts not agreed before the sale) must not carry GST
* Credited and remaining amount shown on the original invoice
* Optional: stop posting a credit note that has errors (company setting)
* Credit note register with filters for problems

Works on Odoo's own credit notes. Does not change tax computation.

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
    ],
    'data': [
        'security/rn_gst_credit_note_security.xml',
        'data/gst_credit_note_reason_data.xml',
        'views/gst_credit_note_reason_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_move_reversal_views.xml',
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
