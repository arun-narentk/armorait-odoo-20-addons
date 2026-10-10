# Architecture: armora_gst_filing (Odoo 20)

Production architecture boundary for **Armora GST Filing**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Return preparation and Offline Tool / upload-file generation from Odoo books. Does not submit to GST Portal.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| armora.gst.filing / filing.line snapshots | GST Portal submission |
| GSTR classification (armora.gst.classification) | Tax calculation |
| Data extraction into filing lines | 2B matching engine |
| Filing validation (armora.gst.filing.validation) | ITC eligibility |
| Excel / upload file generation | Shared pre-API armora.gst.validation (rules) |
| Filing lifecycle states | - |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| armora.gst.filing / filing.line snapshots | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| GSTR classification (armora.gst.classification) | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| Data extraction into filing lines | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| Filing validation (armora.gst.filing.validation) | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| Excel / upload file generation | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| Filing lifecycle states | `armora_gst_filing` | armora_gst_3b, armora_gst_dashboard, armora_gst_analytics |
| Upstream: account.move | External / sibling | `armora_gst_filing` |
| Upstream: l10n_in fields | External / sibling | `armora_gst_filing` |
| Upstream: armora.gst.registration | External / sibling | `armora_gst_filing` |

---

## Dependency graph

```text
Posted Indian invoices
        │
        ▼
Extract / classify → filing lines
        │
        ▼
Validate snapshot → generate upload file
        │
        ▼
Submitted / filed (manual portal status)
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `armora_gst_multi_gstin`, `armora_gst_exception`, `armora_gst_dashboard`

**Consumes:** account.move, l10n_in fields, armora.gst.registration

**Consumed by:** armora_gst_3b, armora_gst_dashboard, armora_gst_analytics

---

## Non-negotiables

- Do not duplicate engines owned by sibling modules.
- Do not invent Odoo APIs or fabricate government / portal evidence.
- Prefer soft optional dependencies; avoid circular hard depends.
- Multi-company safe; multi-GSTIN scoped via `armora.gst.registration` where relevant.
- Structure-valid GSTIN is not government-verified.
- Missing portal data is Unknown / Not observed, not automatic Non-Compliant.

---

## Notes

Snapshot lines lock after load; validation annotations remain writable.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
