# Architecture: armora_gst_customer_compliance (Odoo 20)

Production architecture boundary for **Armora GST Customer Compliance**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Customer/recipient GST profile intelligence before sell/invoice/credit. Not a second GSTIN verifier.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Customer GST compliance profile / snapshots | GSTIN verification engine |
| Compliance assessment / risk / alerts / review | Tax / HSN / rate engines |
| Profile change impact analysis | E-invoice API |
| Sales-side consistency findings | Generic audit / exception frameworks |
| - | Auto-block sales on stale verification (default) |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Customer GST compliance profile / snapshots | `armora_gst_customer_compliance` | Sales UX, dashboard, audit |
| Compliance assessment / risk / alerts / review | `armora_gst_customer_compliance` | Sales UX, dashboard, audit |
| Profile change impact analysis | `armora_gst_customer_compliance` | Sales UX, dashboard, audit |
| Sales-side consistency findings | `armora_gst_customer_compliance` | Sales UX, dashboard, audit |
| Upstream: Partner VAT/treatment | External / sibling | `armora_gst_customer_compliance` |
| Upstream: POS helpers | External / sibling | `armora_gst_customer_compliance` |
| Upstream: validator issues | External / sibling | `armora_gst_customer_compliance` |
| Upstream: verification evidence | External / sibling | `armora_gst_customer_compliance` |

---

## Dependency graph

```text
Customer master + verified evidence
        │
        ▼
Assessment controls → risk / alerts
        │
        ▼
Transaction consistency (soft) → review workflow
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `verification`, `invoice_validator`, `HSN`, `rate`, `einvoice_monitor`, `audit`, `exception`

**Consumes:** Partner VAT/treatment, POS helpers, validator issues, verification evidence

**Consumed by:** Sales UX, dashboard, audit

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

E-invoice enablement ≠ legal applicability. Format valid ≠ government verified.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
