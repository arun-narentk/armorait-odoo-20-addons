# Architecture: armora_gst_sales_reconciliation (Odoo 20)

Production architecture boundary for **Armora GST Sales Reconciliation**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Outward books vs return / customer reporting reconciliation. Not filing engine.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Sales reconciliation runs / matches (target) | GSTR-1 generation (filing) |
| Outward mismatch findings | Customer compliance profile |
| - | E-invoice API |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Sales reconciliation runs / matches (target) | `armora_gst_sales_reconciliation` | Analytics, customer compliance, dashboard |
| Outward mismatch findings | `armora_gst_sales_reconciliation` | Analytics, customer compliance, dashboard |
| Upstream: out_invoice / refunds | External / sibling | `armora_gst_sales_reconciliation` |
| Upstream: filing lines when available | External / sibling | `armora_gst_sales_reconciliation` |

---

## Dependency graph

```text
Sales invoices ↔ return / expected reporting
        │
        ▼
Match states → findings
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `filing`, `customer_compliance`, `exception`, `dashboard`

**Consumes:** out_invoice / refunds, filing lines when available

**Consumed by:** Analytics, customer compliance, dashboard

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

Sibling to purchase recon; do not merge engines.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
