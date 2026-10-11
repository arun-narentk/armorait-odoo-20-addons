# -*- coding: utf-8 -*-
{
    'name': 'Armora GSTIN Verification',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTIN check history per customer and vendor: structure, GST portal status and manual checks with proof | ARMORA IT Technologies',
    'description': """
Armora GSTIN Verification
=========================
Part of the Armora GST Suite for Odoo 20.

* Check history on each customer and vendor: who checked, when, how, and the result
* Structure check: format, checksum and state code against the partner's state
* GST portal status through Odoo's own GSTIN status service (Indian Accounting setting
  "Check GST Number Status", uses IAP credits), when that setting is on
* Manual check: record what you saw on the GST portal, with a screenshot as proof
* Partner status: Active, Inactive, Structure OK, Structure Invalid, Not Checked, Check Unavailable
* "Re-check due" filter for partners whose last portal or manual check is older than
  the number of days set on the company (180 by default)
* Daily job runs the free structure check on partners with a GSTIN

A valid structure is not a government verification. When the status service cannot be
reached, the result is saved as "Check Unavailable", never as Active.

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
        'security/rn_gstin_verification_security.xml',
        'data/gstin_verification_data.xml',
        'views/gst_gstin_check_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/gstin_manual_check_wizard_views.xml',
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
