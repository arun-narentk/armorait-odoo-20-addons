# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Invoice Validator',
    'version': '20.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'Pre-filing GST invoice quality gate for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Invoice Validator for Odoo 20
=======================================
GST invoice quality-control layer for the Armora GST Suite.

Validate sales invoices, vendor bills, credit notes and debit notes
before filing, reconciliation, E-Invoice or E-Way Bill workflows.

Checks include:

* GSTIN structure / checksum (via rn_gst_base)
* Place of supply consistency
* HSN/SAC prerequisites
* GST tax type consistency
* Document / credit-note references
* Export / SEZ / reverse-charge signals
* E-Invoice and E-Way Bill prerequisites (no API submit)

Does NOT:

* File GST returns or upload to GST Portal
* Generate GSTR-1 / reconcile GSTR-2B
* Generate E-Invoices or E-Way Bills
* Determine final ITC eligibility
* Guarantee legal GST compliance

Depends on rn_gst_base. Complements Odoo l10n_in.

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
        'security/gst_invoice_validator_security.xml',
        'data/gst_invoice_validator_data.xml',
        'views/gst_configuration_views.xml',
        'views/account_move_views.xml',
        'views/gst_invoice_issue_views.xml',
        'views/gst_invoice_validation_views.xml',
        'views/gst_invoice_validation_line_views.xml',
        'views/gst_invoice_validation_wizard_views.xml',
        'views/gst_menus.xml',
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
