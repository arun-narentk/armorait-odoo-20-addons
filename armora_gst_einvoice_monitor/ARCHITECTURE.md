# Architecture: armora_gst_einvoice_monitor (Odoo 20)

Production architecture boundary for **Armora GST E-Invoice Monitor**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

IRN lifecycle monitoring views. No portal API client.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Accountant monitor lists / KPIs for IRN states (target) | IRP API |
| Pending / failed / cancelled surfaces | Ship-to field engine (einvoice) |
| - | Invoice tax validation |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Accountant monitor lists / KPIs for IRN states (target) | `armora_gst_einvoice_monitor` | Dashboard, compliance modules |
| Pending / failed / cancelled surfaces | `armora_gst_einvoice_monitor` | Dashboard, compliance modules |
| Upstream: EDI document states / armora_einvoice fields | External / sibling | `armora_gst_einvoice_monitor` |

---

## Dependency graph

```text
EDI / einvoice statuses → monitor aggregations → drill-down
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `armora_gst_einvoice`, `l10n_in_edi`, `dashboard`, `customer/vendor compliance`

**Consumes:** EDI document states / armora_einvoice fields

**Consumed by:** Dashboard, compliance modules

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

Never fabricate IRNs or government responses.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
