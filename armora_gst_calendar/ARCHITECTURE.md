# Architecture: armora_gst_calendar (Odoo 20)

Production architecture boundary for **Armora GST Compliance Calendar**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Deadlines and obligations from effective-dated rules + extensions. Not hardcoded 11th/20th.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Obligation / deadline generation (target) | Filing engine |
| Extension / holiday adjustments (config) | calendar.event as source of truth for obligations |
| Calendar views of GST duties | Hardcoded due dates in Python |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Obligation / deadline generation (target) | `armora_gst_calendar` | Dashboard, notifications |
| Extension / holiday adjustments (config) | `armora_gst_calendar` | Dashboard, notifications |
| Calendar views of GST duties | `armora_gst_calendar` | Dashboard, notifications |
| Upstream: armora.gst.period | External / sibling | `armora_gst_calendar` |
| Upstream: rule config | External / sibling | `armora_gst_calendar` |

---

## Dependency graph

```text
Period + registration
        │
        ▼
Rule-driven deadlines → obligations
        │
        ▼
Sync status from filing when available
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `filing`, `exception`, `dashboard`

**Consumes:** armora.gst.period, rule config

**Consumed by:** Dashboard, notifications

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

Missing filing data → Unknown / pending, not auto non-compliant.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
