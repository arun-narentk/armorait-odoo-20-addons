# -*- coding: utf-8 -*-
{
    'name': 'Armora GST HSN/SAC Validator',
    'version': '20.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Validate HSN/SAC codes on products and invoices for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST HSN/SAC Validator
===========================
Part of the Armora GST Suite for Odoo 20.

* Check HSN/SAC length and digit rules (reuse l10n_in + armora_gst_base)
* Product and invoice-line classification completeness
* Validation results, runs and rule registry shells
* Bulk validation wizard shell

Does NOT:

* Replace Odoo tax computation or chart of accounts
* Ship a government HSN/SAC master database
* Claim government approval from format validation alone
* Depend on armora_gst_invoice_validator (that module may consume this later)

Depends on armora_gst_base. Complements Odoo l10n_in.

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
    ],
    'data': [
        'security/armora_gst_hsn_validator_security.xml',
        'data/hsn_validation_data.xml',
        'views/hsn_validation_result_views.xml',
        'views/hsn_validation_run_views.xml',
        'views/hsn_validation_rule_views.xml',
        'views/hsn_wizard_views.xml',
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
    'price': 5.00,
    'currency': 'USD',
}
