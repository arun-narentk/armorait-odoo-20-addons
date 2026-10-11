# Architecture: rn_gst_filing (Odoo 20)

Production architecture boundary for **Armora GST Filing**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Return preparation and Offline Tool / upload-file generation from Odoo books. Does not submit to GST Portal.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| rn.gst.filing / filing.line snapshots | GST Portal submission |
| GSTR classification (rn.gst.classification) | Tax calculation |
| Data extraction into filing lines | 2B matching engine |
| Filing validation (rn.gst.filing.validation) | ITC eligibility |
| Excel / upload file generation | Shared pre-API rn.gst.rule.validation (rules) |
| Filing lifecycle states | - |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| rn.gst.filing / filing.line snapshots | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| GSTR classification (rn.gst.classification) | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| Data extraction into filing lines | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| Filing validation (rn.gst.filing.validation) | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| Excel / upload file generation | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| Filing lifecycle states | `rn_gst_filing` | rn_gst_3b, rn_gst_dashboard, rn_gst_analytics |
| Upstream: account.move | External / sibling | `rn_gst_filing` |
| Upstream: l10n_in fields | External / sibling | `rn_gst_filing` |
| Upstream: rn.gst.registration | External / sibling | `rn_gst_filing` |

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

**Hard depends:** `rn_gst_base`

**Soft / optional:** `rn_gst_multi_gstin`, `rn_gst_exception`, `rn_gst_dashboard`

**Consumes:** account.move, l10n_in fields, rn.gst.registration

**Consumed by:** rn_gst_3b, rn_gst_dashboard, rn_gst_analytics

---

## Non-negotiables

- Do not duplicate engines owned by sibling modules.
- Do not invent Odoo APIs or fabricate government / portal evidence.
- Prefer soft optional dependencies; avoid circular hard depends.
- Multi-company safe; multi-GSTIN scoped via `rn.gst.registration` where relevant.
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
