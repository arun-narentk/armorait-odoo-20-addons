# Architecture: armora_gst_export (Odoo 20)

Production architecture boundary for **Armora GST Export Compliance**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Export / SEZ / LUT compliance and refund readiness. Not logistics or ICEGATE.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Export compliance profile / checklist (target) | Shipping logistics |
| LUT / IGST path readiness signals | ICEGATE filing |
| Shipping bill / BRC-FIRC evidence tracking (where data exists) | Tax calculation |
| Refund readiness indicators | E-invoice API |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Export compliance profile / checklist (target) | `armora_gst_export` | Filing, invoice compliance, dashboard |
| LUT / IGST path readiness signals | `armora_gst_export` | Filing, invoice compliance, dashboard |
| Shipping bill / BRC-FIRC evidence tracking (where data exists) | `armora_gst_export` | Filing, invoice compliance, dashboard |
| Refund readiness indicators | `armora_gst_export` | Filing, invoice compliance, dashboard |
| Upstream: l10n_in export fields | External / sibling | `armora_gst_export` |
| Upstream: fiscal positions Export/SEZ | External / sibling | `armora_gst_export` |

---

## Dependency graph

```text
Export invoice → documentary / LUT checks → readiness
        │
        ▼
Soft filing / e-invoice adapters
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `einvoice`, `filing`, `invoice_validator`, `exception`

**Consumes:** l10n_in export fields, fiscal positions Export/SEZ

**Consumed by:** Filing, invoice compliance, dashboard

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

No fabricated government refund acknowledgements.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
