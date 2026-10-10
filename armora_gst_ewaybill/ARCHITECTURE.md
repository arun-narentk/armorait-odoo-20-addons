# Architecture: armora_gst_ewaybill (Odoo 20)

Production architecture boundary for **Armora GST E-Way Bill**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

EWB extensions including closure flows on top of Odoo e-waybill EDI/stock.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| EWB closure service / wizards | Core IRP e-invoice engine |
| Closure validation and audit logging | Stock logistics replacement |
| Move EWB status extensions | Monitor-only UI (ewaybill_manager) |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| EWB closure service / wizards | `armora_gst_ewaybill` | ewaybill_manager, dashboard |
| Closure validation and audit logging | `armora_gst_ewaybill` | ewaybill_manager, dashboard |
| Move EWB status extensions | `armora_gst_ewaybill` | ewaybill_manager, dashboard |
| Upstream: Odoo EWB EDI | External / sibling | `armora_gst_ewaybill` |
| Upstream: rules/api.audit | External / sibling | `armora_gst_ewaybill` |

---

## Dependency graph

```text
Active EWB → close validate → API (or mock) → status/audit
```

**Hard depends:** `armora_gst_einvoice`, `l10n_in_edi_ewaybill`, `l10n_in_ewaybill_stock`, `stock`

**Soft / optional:** `exception`, `dashboard`

**Consumes:** Odoo EWB EDI, rules/api.audit

**Consumed by:** ewaybill_manager, dashboard

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

Do not call portal from analytics/compliance consumers.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
