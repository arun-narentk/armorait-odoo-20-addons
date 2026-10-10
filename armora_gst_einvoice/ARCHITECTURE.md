# Architecture: armora_gst_einvoice (Odoo 20)

Production architecture boundary for **Armora GST E-Invoice Extensions**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Enhances Odoo l10n_in_edi flows (ship-to, validation summary). Does not replace IRP engine.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Ship-to / export ship detail fields on moves | IRP HTTP client replacement |
| Pre-API validation hooks via armora.gst.validation | Fabricating IRNs |
| Display helpers for IRN / status from EDI | E-way bill close engine (ewaybill module) |
| - | Monitor UI (einvoice_monitor) |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Ship-to / export ship detail fields on moves | `armora_gst_einvoice` | armora_gst_ewaybill, einvoice_monitor, dashboard |
| Pre-API validation hooks via armora.gst.validation | `armora_gst_einvoice` | armora_gst_ewaybill, einvoice_monitor, dashboard |
| Display helpers for IRN / status from EDI | `armora_gst_einvoice` | armora_gst_ewaybill, einvoice_monitor, dashboard |
| Upstream: Odoo EDI | External / sibling | `armora_gst_einvoice` |
| Upstream: rules validation | External / sibling | `armora_gst_einvoice` |

---

## Dependency graph

```text
Invoice → rules validation → Odoo EDI IRN
        │
        ▼
Armora display / ship-to constraints
```

**Hard depends:** `armora_gst_rules`, `l10n_in_edi`, `l10n_in_edi_ewaybill`

**Soft / optional:** `invoice_validator`, `exception`

**Consumes:** Odoo EDI, rules validation

**Consumed by:** armora_gst_ewaybill, einvoice_monitor, dashboard

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

Enablement ≠ applicability. Complements monitor module.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
