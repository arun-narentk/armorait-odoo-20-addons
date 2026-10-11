# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Vendor Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Vendor GST compliance monitoring for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Vendor Compliance
===========================
Part of the Armora GST Suite for Odoo 20.

* Monitor vendor GSTIN completeness and verification status
* Highlight vendors with repeated GST document issues
* Support purchase-side compliance reviews

Partner-centric compliance. Does not scrape GST Portal data by default.

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
        'security/armora_gst_vendor_compliance_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': False,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
