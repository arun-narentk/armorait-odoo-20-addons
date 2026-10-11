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

Hard dependency: rn_gst_base only.

Optional integrations (detected at runtime, not required to install):

* rn_gst_filing
* rn_gst_2b_reconciliation
* rn_gst_invoice_validator
* rn_gst_itc (when implemented)
* rn_gst_einvoice / rn_gst_einvoice_monitor
* rn_gst_ewaybill / rn_gst_ewaybill_manager
* rn_gst_exception (when implemented)
* rn_gst_3b
* rn_gst_multi_gstin / rn.gst.registration
* rn_gst_audit / rn_gst_calendar (when implemented)

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
        'rn_gst_base',
    ],
    'data': [
        'security/gst_dashboard_security.xml',
        'data/gst_dashboard_data.xml',
        'views/gst_dashboard_views.xml',
        'views/gst_dashboard_config_views.xml',
        'views/gst_kpi_dashboard_views.xml',
        'views/gst_dashboard_menus.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/gst_dashboard_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rn_gst_dashboard/static/src/kpi_dashboard/**/*',
        ],
    },
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
