# -*- coding: utf-8 -*-
{
    'name': 'Armora GST E-Invoice Monitor',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Watch IRN status of every invoice: pending, failed, generated, cancelled, 24-hour cancel window, 30-day limit | ARMORA IT Technologies',
    'description': """
Armora GST E-Invoice Monitor
============================
Part of the Armora GST Suite for Odoo 20.

* One e-invoice status per invoice from Odoo's Indian e-invoicing: Pending, Failed,
  IRN Generated, Cancelled, or "Cancel IRN" when the invoice was cancelled in Odoo
  but its IRN is still live
* IRN, acknowledgement number and date kept on the invoice
* 24-hour IRN cancel window: which invoices can still be cancelled on the IRP, and until when
* 30-day reporting limit for companies with turnover of 10 crore or more (setting):
  invoices still without IRN after 30 days
* Monitor list, kanban and pivot with filters for each case, and "Send Again" for failed ones
* Daily job fills IRN details for invoices sent before this app was installed

Uses Odoo's l10n_in_edi to send and cancel. No second IRP client.

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
        'l10n_in_edi',
    ],
    'data': [
        'data/einvoice_monitor_cron.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
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
