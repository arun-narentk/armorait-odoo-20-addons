# Odoo 20 Indian GST Analysis (for Armora GST Suite)

Technical report based on Odoo 20 community source in this workspace (`addons/l10n_in`) and Odoo 20 documentation. Enterprise modules such as `l10n_in_reports_gstr` are referenced from documentation but are not present in this community-only tree.

**Do not modify Odoo core.** Armora modules layer workflow on top.

---

## 1. Existing Odoo GST models (community)

| Area | Models / modules |
|------|-------------------|
| Localization | `l10n_in` |
| Partners | `res.partner` (+ `l10n_in_gst_treatment`, GSTIN via `vat`) |
| Invoices | `account.move`, `account.move.line` |
| Taxes | `account.tax` (+ Indian GST tax types via l10n_in) |
| Company | `res.company` (+ state, VAT/GSTIN) |
| Port codes | `l10n_in.port.code` |
| UOM codes | `l10n_in.uom.code` |

Enterprise (documented, not in this repo):

| Module | Purpose |
|--------|---------|
| `l10n_in_edi` | e-Invoice IRN generation |
| `l10n_in_edi_ewaybill` | E-Way Bill |
| `l10n_in_gstin_status` | GSTIN status verification |
| `l10n_in_reports` | Indian GST reports |
| `l10n_in_reports_gstr` | GSTR filing, 2B retrieval, GSTN API |

---

## 2. Existing GST fields (key)

### `res.partner`

- `l10n_in_gst_treatment` (regular, composition, consumer, overseas, etc.)
- `vat` (GSTIN)
- `l10n_in_gst_state_warning` (computed)

### `account.move`

- `l10n_in_gst_treatment`
- `l10n_in_state_id` (place of supply)
- `l10n_in_shipping_bill_number`, `l10n_in_shipping_bill_date`
- `l10n_in_shipping_port_code_id`
- `country_code` (filter Indian moves)

### Products

- `l10n_in_hsn_code`, `l10n_in_hsn_description`

### Taxes

- Indian CGST/SGST/IGST/Cess via chart template
- `l10n_in_tax_type` on taxes (enterprise/localization metadata)

---

## 3. Existing GST reports

Community `l10n_in` provides chart, taxes, fiscal positions, invoice PDF/report extensions.

Enterprise `l10n_in_reports` / `l10n_in_reports_gstr` (per Odoo 20 docs):

- GSTR-1 filing via GST service
- GSTR-2B import/retrieval
- GST return reports and reconciliation tooling

---

## 4. Existing GSTR functionality

**Odoo Enterprise** handles GSTN-connected return filing and 2B where licensed.

**Armora GST Filing** target:

- Offline Tool Excel workflow (prepare → validate → populate official workbook)
- Does not duplicate Enterprise GSTN API push
- Complements with accountant-friendly snapshot and error remediation

---

## 5. Existing GST APIs

Enterprise GST return modules use Odoo IAP/GSP integration for GSTN (GSTR-1 push, 2B fetch, etc.). Armora should **reuse** this when customers have Enterprise; Armora adds Offline Tool Excel and validation UX for teams that file offline or want a preparatory layer.

---

## 6. E-Invoice functionality

`l10n_in_edi` (Enterprise): IRN generation, JSON to NIC/GSTN.

**Armora should not recreate.** Future Armora modules: monitor/retry/exception center only.

---

## 7. E-Way Bill functionality

`l10n_in_edi_ewaybill` (Enterprise): EWB from invoices/deliveries.

**Armora should not recreate.** Future: expiry dashboard, bulk ops, August 2026 field validations as a monitor layer.

---

## 8. What Armora should reuse

- `l10n_in` GST treatment, POS, HSN, Indian taxes
- Posted `account.move` as source of truth
- Partner GSTIN (`vat`) and state
- Enterprise GSTR/2B API when available (integration point, not V1 filing scope)
- `rn_gst_base` shared GSTIN validator, period helpers, suite menu

---

## 9. What Armora should add

| Armora module | Value add |
|--------------|-----------|
| `rn_gst_filing` | GSTR-1 snapshot, validation, Offline Tool Excel |
| `rn_gst_invoice_validator` | Pre-post invoice checks |
| `rn_gst_2b_reconciliation` | 2B vs bill matching UX |
| `rn_gst_exception` | Central exception hub (planned) |
| `rn_gst_dashboard` | Management GST dashboard (planned) |

Positioning: **detect → explain → fix → reconcile → prepare → file**

---

## 10. Potential conflicts

| Risk | Mitigation |
|------|------------|
| Duplicate GSTR-1 API filing | Armora V1 = Offline Tool Excel only; document Enterprise as Route B |
| Snapshot vs live invoice drift | Regenerate snapshot; filed records locked |
| Template version drift | Admin-uploaded templates with version/effective dates |
| Tax rounding differences | `rn.gst.money` + reconciliation tolerance |
| Mixed-rate Excel rows | Per invoice + rate bucket grouping in generator |
| Overlapping validation with `invoice_validator` | Filing validation at return level; validator at post time |

---

## Armora GST Filing implementation map

| Spec model | Actual module file |
|------------|-------------------|
| `rn.gst.filing` | `models/gst_filing.py` |
| `rn.gst.filing.line` | `models/gst_filing_line.py` |
| `rn.gst.rule.validation` / results | `models/gst_validation.py` |
| `rn.gst.data.extractor` | `models/gst_data_extractor.py` |
| `rn.gst.classification` | `models/gst_classification.py` |
| `rn.gst.excel.template` | `models/gst_excel_template.py` |
| `rn.gst.excel.generator` | `models/gst_excel_generator.py` |

States implemented: `draft`, `data_loaded`, `validated`, `generated`, `submitted`, `filed`, `cancelled`.
Loading GST data moves the filing to `data_loaded` and locks snapshot lines until an explicit regenerate or reset to draft.
Optional `gst_registration_id` links to `rn.gst.registration` for multi-GSTIN consistency.
Service facades live under `services/` and delegate to AbstractModel engines in `models/`.

---

*Generated for Armora GST Suite planning. Update when Enterprise modules are available in the deployment environment.*
