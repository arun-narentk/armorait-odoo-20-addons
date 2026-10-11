# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Multi-GSTIN',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Run one company with many GST registrations: GSTIN per journal and invoice, IGST or CGST/SGST check | ARMORA IT Technologies',
    'description': """
Armora GST Multi-GSTIN
======================
Part of the Armora GST Suite for Odoo 20.

* Link each sales and purchase journal to one GST registration (GSTIN)
* Every invoice and bill gets the GSTIN of its journal, or the company default
* Inter-state or intra-state supply is worked out from the state of that GSTIN,
  not only the company address
* Warning when an invoice uses CGST/SGST on an inter-state supply, or IGST on an
  intra-state one, with a filter to list all such invoices
* Posting is stopped when the invoice date is outside the registration's
  effective dates, or the registration is archived
* Registration form shows its journals, invoices and bills

Extends rn.gst.registration from rn_gst_base; does not add a second registration table.

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
        'security/rn_gst_multi_gstin_security.xml',
        'views/gst_registration_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
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
    'price': 12.00,
    'currency': 'USD',
}
