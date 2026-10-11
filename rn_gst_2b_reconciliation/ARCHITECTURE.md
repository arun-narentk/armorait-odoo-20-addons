# Architecture: rn_gst_2b_reconciliation (Odoo 20)

Production architecture boundary for **Armora GST GSTR-2B Reconciliation**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Books vs GSTR-2B matching. Owns matching results; does not claim ITC.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| 2B import / storage (rn.gst.gstr2b / .line) | ITC eligibility / reclaim |
| Matching algorithm and match_state | Purchase document matching (purchase_reconciliation) |
| Mismatch amount diffs | Filing GSTR-1 engine |
| 2B reconciliation UX | Portal scraping by default |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| 2B import / storage (rn.gst.gstr2b / .line) | `rn_gst_2b_reconciliation` | rn_gst_itc, rn_gst_dashboard, rn_gst_analytics, vendor compliance |
| Matching algorithm and match_state | `rn_gst_2b_reconciliation` | rn_gst_itc, rn_gst_dashboard, rn_gst_analytics, vendor compliance |
| Mismatch amount diffs | `rn_gst_2b_reconciliation` | rn_gst_itc, rn_gst_dashboard, rn_gst_analytics, vendor compliance |
| 2B reconciliation UX | `rn_gst_2b_reconciliation` | rn_gst_itc, rn_gst_dashboard, rn_gst_analytics, vendor compliance |
| Upstream: Vendor bills (account.move) | External / sibling | `rn_gst_2b_reconciliation` |
| Upstream: Imported 2B rows | External / sibling | `rn_gst_2b_reconciliation` |

---

## Dependency graph

```text
Import 2B → Match to bills → match_state
        │
        ▼
Aggregates / drill-down → soft ITC / dashboard / vendor risk
```

**Hard depends:** `rn_gst_base`

**Soft / optional:** `rn_gst_exception`, `rn_gst_itc`, `rn_gst_dashboard`, `rn_gst_vendor_compliance`

**Consumes:** Vendor bills (account.move), Imported 2B rows

**Consumed by:** rn_gst_itc, rn_gst_dashboard, rn_gst_analytics, vendor compliance

---

## Non-negotiables

- Do not duplicate engines owned by sibling modules.
- Do not invent Odoo APIs or fabricate government / portal evidence.
- Prefer soft optional dependencies; avoid circular hard depends.
- Multi-company safe; multi-GSTIN scoped via `rn.gst.registration` where relevant.
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
