# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Credit Note',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST-aware credit note checks and workflows for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Credit Note
=====================
Part of the Armora GST Suite for Odoo 20.

* Validate credit note GST references and tax treatment
* Link credit notes to original invoices where required
* Surface GST completeness issues before posting/filing

Works with standard customer/vendor credit notes. Related: armora_invoice_credit_notes.

Depends on armora_gst_base. Does not replace Odoo l10n_in / EDI engines.

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
        'security/armora_gst_credit_note_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
