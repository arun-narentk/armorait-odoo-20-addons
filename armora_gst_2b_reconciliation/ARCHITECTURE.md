# Architecture: armora_gst_2b_reconciliation (Odoo 20)

Production architecture boundary for **Armora GST GSTR-2B Reconciliation**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Books vs GSTR-2B matching. Owns matching results; does not claim ITC.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| 2B import / storage (armora.gst.gstr2b / .line) | ITC eligibility / reclaim |
| Matching algorithm and match_state | Purchase document matching (purchase_reconciliation) |
| Mismatch amount diffs | Filing GSTR-1 engine |
| 2B reconciliation UX | Portal scraping by default |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| 2B import / storage (armora.gst.gstr2b / .line) | `armora_gst_2b_reconciliation` | armora_gst_itc, armora_gst_dashboard, armora_gst_analytics, vendor compliance |
| Matching algorithm and match_state | `armora_gst_2b_reconciliation` | armora_gst_itc, armora_gst_dashboard, armora_gst_analytics, vendor compliance |
| Mismatch amount diffs | `armora_gst_2b_reconciliation` | armora_gst_itc, armora_gst_dashboard, armora_gst_analytics, vendor compliance |
| 2B reconciliation UX | `armora_gst_2b_reconciliation` | armora_gst_itc, armora_gst_dashboard, armora_gst_analytics, vendor compliance |
| Upstream: Vendor bills (account.move) | External / sibling | `armora_gst_2b_reconciliation` |
| Upstream: Imported 2B rows | External / sibling | `armora_gst_2b_reconciliation` |

---

## Dependency graph

```text
Import 2B → Match to bills → match_state
        │
        ▼
Aggregates / drill-down → soft ITC / dashboard / vendor risk
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `armora_gst_exception`, `armora_gst_itc`, `armora_gst_dashboard`, `armora_gst_vendor_compliance`

**Consumes:** Vendor bills (account.move), Imported 2B rows

**Consumed by:** armora_gst_itc, armora_gst_dashboard, armora_gst_analytics, vendor compliance

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

Unknown / missing portal data must not auto-become ITC ineligible.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
