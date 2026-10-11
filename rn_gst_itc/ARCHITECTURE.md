# Architecture: rn_gst_itc (Odoo 20)

Production architecture boundary for **Armora GST ITC**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

ITC eligibility / blocked / reverse / reclaim ledger after reconciliation. Not accounting or 2B matching.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| ITC decision records (target) | GSTR-2B import/match (2b module) |
| Eligibility / ineligible / blocked / reverse / reclaim workflows | 3B set-off only (rn.gst.itc.utilization in 3b) |
| Supplier-level ITC risk signals for consumers | Purchase document recon |
| - | Portal claim submission |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| ITC decision records (target) | `rn_gst_itc` | 3B utilization, analytics, vendor compliance |
| Eligibility / ineligible / blocked / reverse / reclaim workflows | `rn_gst_itc` | 3B utilization, analytics, vendor compliance |
| Supplier-level ITC risk signals for consumers | `rn_gst_itc` | 3B utilization, analytics, vendor compliance |
| Upstream: 2B match results | External / sibling | `rn_gst_itc` |
| Upstream: vendor bills | External / sibling | `rn_gst_itc` |
| Upstream: accounting tax | External / sibling | `rn_gst_itc` |

---

## Dependency graph

```text
2B / books evidence
        │
        ▼
ITC decision (eligible / blocked / reverse / reclaim)
        │
        ▼
Signals to 3B / analytics / vendor risk
```

**Hard depends:** `rn_gst_base`

**Soft / optional:** `2b`, `purchase_recon`, `exception`, `vendor_compliance`, `dashboard`, `3b`

**Consumes:** 2B match results, vendor bills, accounting tax

**Consumed by:** 3B utilization, analytics, vendor compliance

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

GSTR-2B matched ≠ automatically eligible ITC.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
