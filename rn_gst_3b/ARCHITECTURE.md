# Architecture: rn_gst_3b (Odoo 20)

Production architecture boundary for **Armora GST GSTR-3B**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

3B liability / interest / ITC utilization set-off helpers linked to filing. Not full ITC ledger.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| rn.gst.3b records and liability breakup | ITC eligibility / blocked credit (rn_gst_itc) |
| Interest calculator (rule-driven) | Portal 3B submit |
| ITC utilization set-off engine (rn.gst.itc.utilization) | GSTR-1 extraction (filing) |
| Link from GSTR-1 filing to 3B | Hard-coded utilization priority outside rules |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| rn.gst.3b records and liability breakup | `rn_gst_3b` | Dashboard, Analytics |
| Interest calculator (rule-driven) | `rn_gst_3b` | Dashboard, Analytics |
| ITC utilization set-off engine (rn.gst.itc.utilization) | `rn_gst_3b` | Dashboard, Analytics |
| Link from GSTR-1 filing to 3B | `rn_gst_3b` | Dashboard, Analytics |
| Upstream: Filing totals | External / sibling | `rn_gst_3b` |
| Upstream: ITC_UTILIZATION rules | External / sibling | `rn_gst_3b` |

---

## Dependency graph

```text
GSTR-1 / books liability
        │
        ▼
3B liability + self-assessed controls
        │
        ▼
ITC utilization (rule priority) → interest if configured
```

**Hard depends:** `rn_gst_rules`, `rn_gst_filing`, `mail`

**Soft / optional:** `rn_gst_itc`, `rn_gst_dashboard`

**Consumes:** Filing totals, ITC_UTILIZATION rules

**Consumed by:** Dashboard, Analytics

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

Utilization ≠ eligibility. Do not invent ITC from 2B alone.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
