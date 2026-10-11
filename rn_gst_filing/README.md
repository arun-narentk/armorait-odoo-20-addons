# Armora GST Filing

GSTR-1 filing preparation for Odoo 20 Indian companies. Part of the **Armora GST Suite**.

## Overview

Armora GST Filing extracts posted customer invoices and credit notes into an auditable **filing snapshot**, validates GST data, and populates an administrator-uploaded **GSTN Returns Offline Tool** Excel workbook.

The generated `.xlsx` is **not** uploaded directly to the GST Portal. Import it into the GSTN Returns Offline Tool, which generates the JSON required for portal upload.

## Features

- GSTR-1 filing snapshot from Odoo accounting
- GST classification (B2B, B2CL, B2CS, export, CDNR/CDNUR, nil/exempt)
- Validation engine with blocking errors and fix hints
- Reconciliation vs posted invoice totals
- Official GSTN Offline Tool Excel template upload and mapping
- Excel generation with text-safe GSTIN/invoice/HSN fields
- Multi-company security and role-based access
- Filing workflow: draft → data_loaded → validated → generated → submitted → filed
- Optional link to `rn.gst.registration` for multi-GSTIN companies
- Snapshot locked after data load (explicit regenerate only)

## Requirements

- Odoo **18.0**
- Indian localization installed (`l10n_in`)
- **rn_gst_base** (Armora GST Suite foundation)
- Python package **openpyxl**

## Dependencies

| Module | Purpose |
|--------|---------|
| `rn_gst_base` | Shared GSTIN, period, money helpers, suite menu |
| `account` | Via rn_gst_base |
| `l10n_in` | Via rn_gst_base |
| `mail` | Chatter on filing records |

Optional (not required): Odoo Enterprise `l10n_in_reports_gstr` for GSTN API filing.

## Installation

1. Copy `rn_gst_base` and `rn_gst_filing` into your Odoo addons path.
2. Install Python dependency: `pip install openpyxl`
3. Restart Odoo.
4. Update Apps List.
5. Install **Armora GST** (base) then **Armora GST Filing**.
6. Configure company GSTIN and Indian accounting.

## Configuration

1. Go to **Armora GST → Configuration → Settings**.
2. Set **B2CL Threshold** and **Reconciliation Tolerance**.
3. As **GST Filing Administrator**, upload the current official GSTN Returns Offline Tool GSTR-1/IFF Excel template under **Filing → Offline Tool Templates**.

## GSTN Excel Template

Do **not** hard-code GSTN workbook layouts. Administrators upload the official template from the GSTN Returns Offline Tool when GSTN releases a new version.

Use **Inspect Workbook** on the template record to build sheet/header mapping.

## GSTR-1 Workflow

```text
Odoo posted invoices
    → Load GST Data (snapshot, state=data_loaded, lines locked)
    → Validate (fix errors on source invoices)
    → Regenerate Snapshot if needed (manager)
    → Generate GST Upload File (Offline Tool Excel)
    → Download workbook
    → Import into GSTN Returns Offline Tool
    → Offline Tool JSON
    → Upload JSON to GST Portal
    → Mark Submitted / Mark Filed in Odoo
```

## Security

| Group | Capabilities |
|-------|----------------|
| Filing User | Create filings, load data, validate, generate Excel |
| Filing Manager | Regenerate snapshot, mark submitted/filed |
| Filing Administrator | Manage Offline Tool templates |

Filed and cancelled returns are read-only.

## Multi-company

Filings, lines, validation results and templates are scoped by company with record rules.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Cannot generate Excel | Fix blocking validation errors first |
| Template not found | Upload and activate an Offline Tool template |
| Reconciliation mismatch | Review tolerance in GST settings; fix source invoices |
| Missing HSN errors | Set HSN/SAC on products or invoice lines |
| openpyxl error | Install `openpyxl` in Odoo Python environment |

## Testing

```bash
odoo-bin -d TEST_DB -i rn_gst_base,rn_gst_filing --test-enable --stop-after-init
```

Or run tagged tests: `rn_gst_filing` post_install suite.

## Known Limitations

- V1 scope is **GSTR-1** Offline Tool Excel export (not GSTR-3B summary engine).
- Does not replace Odoo e-Invoice, E-Way Bill or Enterprise GSTN API filing.
- Template compatibility depends on official GSTN workbook structure; inspect after each GSTN template update.
- Dashboard is a filing list view (not a custom JS dashboard).
- Demo data for screenshots is not bundled; see `static/description/screenshots/SCREENSHOTS.md`.

## Apps Store Assets

- `static/description/index.html` - Odoo Apps module description
- `static/description/icon.png` - Module icon
- `static/description/screenshots/` - Capture plan (add PNGs before publishing)

## Author

**ARMORA IT Technologies**  
https://www.armorait.com/  
info@armorait.com

License: OPL-1
