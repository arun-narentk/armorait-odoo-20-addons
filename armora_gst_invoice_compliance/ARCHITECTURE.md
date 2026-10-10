# Architecture: armora_gst_invoice_compliance (Odoo 20)

Production architecture boundary for **Armora GST Invoice Compliance**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Lifecycle / control / readiness orchestration over validator findings. Not a second detection engine.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Invoice compliance status / review workflow (target) | Issue detection (invoice_validator) |
| Readiness signals for filing / EDI | Tax calculation |
| Aggregation of multi-source invoice compliance context | Filing generation |
| - | Competing post gate / score (avoid fork) |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Invoice compliance status / review workflow (target) | `armora_gst_invoice_compliance` | Dashboard, Audit |
| Readiness signals for filing / EDI | `armora_gst_invoice_compliance` | Dashboard, Audit |
| Aggregation of multi-source invoice compliance context | `armora_gst_invoice_compliance` | Dashboard, Audit |
| Upstream: Validator issues / status | External / sibling | `armora_gst_invoice_compliance` |

---

## Dependency graph

```text
Validator findings + soft specialists
        │
        ▼
Compliance orchestration / review
        │
        ▼
Readiness for filing / EDI / audit
```

**Hard depends:** `armora_gst_base`, `armora_gst_invoice_validator`

**Soft / optional:** `HSN`, `rate`, `GSTIN verification`, `export`, `CN/DN`, `einvoice`, `exception`, `filing`

**Consumes:** Validator issues / status

**Consumed by:** Dashboard, Audit

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

Must not install a second blocking gate that fights the validator.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
