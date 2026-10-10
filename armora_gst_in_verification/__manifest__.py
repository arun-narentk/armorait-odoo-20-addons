# -*- coding: utf-8 -*-
{
    'name': 'Armora GSTIN Verification',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTIN structure checks and verification workflows for Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GSTIN Verification
========================
Part of the Armora GST Suite for Odoo 20.

* Reuse Armora GSTIN structural validation
* Store verification results and review status
* Support partner and company GSTIN checks without inventing portal claims

Does not claim GST Portal API access unless separately configured. Complements the GSTIN status check of Odoo l10n_in.

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
        'security/armora_gst_in_verification_security.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': [
        'static/description/icon.png',
    ],
    'installable': False,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
