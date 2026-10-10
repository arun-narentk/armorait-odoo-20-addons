# -*- coding: utf-8 -*-
{
    'name': 'Armora GST Filing',
    'version': '20.0.1.4.0',
    'category': 'Accounting/Accounting',
    'summary': 'Prepare GSTR-1 and generate GSTN Offline Tool Excel from Odoo 20 | ARMORA IT Technologies',
    'description': """
Armora GST Filing for Odoo 20
============================
Part of the Armora GST Suite.

Prepare GSTR-1 filing data from posted Indian GST invoices:

* Extract accounting data into an auditable filing snapshot
* Classify B2B, B2CL, B2CS, export, credit/debit notes
* Validate GSTIN, HSN/SAC, place of supply and tax totals
* Populate an official GSTN Returns Offline Tool Excel workbook

Workflow:
Load GST Data → Validate → Generate GST Upload File → Download
→ import into GSTN Returns Offline Tool → Offline Tool JSON
→ upload JSON to the GST Portal.

The generated workbook is not uploaded directly to the GST Portal.

Blocking validation errors prevent Excel generation.

Depends on armora_gst_base. Complements Odoo l10n_in and Enterprise
GST return tools; does not replace e-Invoice or E-Way Bill engines.

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
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/gst_filing_security.xml',
        'data/gst_filing_sequence.xml',
        'data/gst_filing_data.xml',
        'views/gst_excel_template_views.xml',
        'views/gst_filing_line_views.xml',
        'views/gst_filing_views.xml',
        'views/gst_filing_wizard_views.xml',
        'views/gst_filing_menus.xml',
        'report/gstr1_summary_report.xml',
        'views/gst_filing_report_views.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        # 'demo/gst_filing_demo.xml',  # enable after fictional demo records are ready
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 29.00,
    'currency': 'USD',
}
