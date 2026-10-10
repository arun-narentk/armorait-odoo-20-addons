# Architecture: armora_gst_purchase_reconciliation (Odoo 20)

Production architecture boundary for **Armora GST Purchase Reconciliation**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Purchase documents vs books matching. Not 2B portal recon and not ITC.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Purchase reconciliation runs / matches (target) | GSTR-2B matching |
| Bill vs PO/GRN/document consistency | ITC eligibility |
| Purchase mismatch findings | Vendor compliance scoring |
| - | Accounting posting |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Purchase reconciliation runs / matches (target) | `armora_gst_purchase_reconciliation` | ITC, vendor compliance, analytics |
| Bill vs PO/GRN/document consistency | `armora_gst_purchase_reconciliation` | ITC, vendor compliance, analytics |
| Purchase mismatch findings | `armora_gst_purchase_reconciliation` | ITC, vendor compliance, analytics |
| Upstream: account.move in_invoice | External / sibling | `armora_gst_purchase_reconciliation` |
| Upstream: purchase.order when present | External / sibling | `armora_gst_purchase_reconciliation` |

---

## Dependency graph

```text
Vendor bill ↔ purchase docs
        │
        ▼
Match / mismatch → findings
        │
        ▼
Soft handoff to ITC / vendor risk
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `purchase`, `2b`, `itc`, `vendor_compliance`, `exception`

**Consumes:** account.move in_invoice, purchase.order when present

**Consumed by:** ITC, vendor compliance, analytics

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

Keep separate from armora_gst_2b_reconciliation.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
