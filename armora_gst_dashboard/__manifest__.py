# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Compliance Dashboard',
    'version': '20.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'Central management dashboard for Armora Indian GST | ARMORA IT Technologies',
    'description': """
Armora GST Compliance Dashboard for Odoo 20
==========================================
Aggregation and visualization layer for the Armora GST Suite.

Monitors GST filings, GSTR-2B reconciliation, invoice validation,
exceptions and related compliance activities when those modules are
installed. Does not recalculate GST business rules.

Hard dependency: armora_gst_base only.

Optional integrations (detected at runtime, not required to install):

* armora_gst_filing
* armora_gst_2b_reconciliation
* armora_gst_invoice_validator
* armora_gst_itc (when implemented)
* armora_gst_einvoice / armora_gst_einvoice_monitor
* armora_gst_ewaybill / armora_gst_ewaybill_manager
* armora_gst_exception (when implemented)
* armora_gst_3b
* armora_gst_multi_gstin / armora.gst.registration
* armora_gst_audit / armora_gst_calendar (when implemented)

Does NOT:

* File GST returns or upload to the GST Portal
* Match GSTR-2B, validate invoices, or compute ITC eligibility
* Generate E-Invoices or E-Way Bills
* Guarantee legal GST compliance

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
        'security/gst_dashboard_security.xml',
        'data/gst_dashboard_data.xml',
        'views/gst_dashboard_views.xml',
        'views/gst_dashboard_config_views.xml',
        'views/gst_dashboard_menus.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/gst_dashboard_demo.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 9.00,
    'currency': 'USD',
}
