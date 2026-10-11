# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Vendor Compliance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'GST risk score per supplier from GSTIN status, GSTR-2B gaps, Rule 37 and bill errors, with Allow / Warn / Approve / Block | ARMORA IT Technologies',
    'description': """
Armora GST Vendor Compliance
============================
Part of the Armora GST Suite for Odoo 20.

* One GST profile per supplier and company, refreshed from the supplier's real data:
  - GSTIN structure, and the GSTIN check status when Armora GSTIN Verification is installed
  - bills of the last 12 months, and bills with GST validation errors
  - bills missing in GSTR-2B and amounts that differ (Armora GSTR-2B Reconciliation)
  - Rule 37 reversals for late payment (Armora GST ITC)
  - composition or unregistered suppliers that charge GST
* Findings list, score out of 100, and risk: Low, Medium, High or Unknown (no bills yet)
* Purchase decision from the risk: Allow, Warn, Needs Approval, or Block for a cancelled or invalid GSTIN,
  with a manual override and reason
* Warning on the vendor bill, and an optional setting to stop posting bills of blocked suppliers
* Weekly refresh of all supplier profiles

Missing portal data is shown as Unknown, never as non-compliant.

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
        'security/rn_gst_vendor_compliance_security.xml',
        'data/vendor_compliance_cron.xml',
        'views/gst_vendor_profile_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
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
    'price': 12.00,
    'currency': 'USD',
}
