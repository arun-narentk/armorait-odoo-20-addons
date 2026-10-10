# Architecture: armora_gst_ewaybill_manager (Odoo 20)

Production architecture boundary for **Armora GST E-Way Bill Manager**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Operational EWB management UI/monitoring. Soft over ewaybill/EDI; not a second API client.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Manager lists / filters / operational KPIs (target) | EWB generate/close API implementation |
| - | Stock picking engine |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Manager lists / filters / operational KPIs (target) | `armora_gst_ewaybill_manager` | Dashboard |
| Upstream: EWB statuses from Odoo/Armora ewaybill | External / sibling | `armora_gst_ewaybill_manager` |

---

## Dependency graph

```text
EWB source statuses → manager views → drill-down
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `armora_gst_ewaybill`, `l10n_in_edi_ewaybill`, `dashboard`

**Consumes:** EWB statuses from Odoo/Armora ewaybill

**Consumed by:** Dashboard

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

Parallel to einvoice_monitor pattern.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
