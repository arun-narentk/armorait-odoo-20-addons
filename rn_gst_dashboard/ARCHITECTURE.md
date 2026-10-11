# Architecture: rn_gst_dashboard (Odoo 20)

Production architecture boundary for **Armora GST Compliance Dashboard**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Operational current-state KPIs. Soft-consumes specialists. Not analytics / BI history.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| rn.gst.dashboard workspace + refresh | Historical trends / MoM / YoY (analytics) |
| Operational KPI aggregation services | Business rule engines |
| Optional snapshots with freshness flags | Filing / matching / ITC calculation |
| Filter wizard / saved filters | Fabricated portal metrics |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| rn.gst.dashboard workspace + refresh | `rn_gst_dashboard` | Users / managers |
| Operational KPI aggregation services | `rn_gst_dashboard` | Users / managers |
| Optional snapshots with freshness flags | `rn_gst_dashboard` | Users / managers |
| Filter wizard / saved filters | `rn_gst_dashboard` | Users / managers |
| Upstream: Specialist stored counters / moves | External / sibling | `rn_gst_dashboard` |

---

## Dependency graph

```text
Filters (company / GSTIN / period)
        │
        ▼
Soft providers → KPI payload → dashboard form
        │
        ▼
Drill actions to source modules
```

**Hard depends:** `rn_gst_base`

**Soft / optional:** `filing`, `2b`, `validator`, `itc`, `einvoice`, `ewaybill`, `exception`, `3b`, `multi_gstin`

**Consumes:** Specialist stored counters / moves

**Consumed by:** Users / managers

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

Dashboard = NOW. Analytics = TREND. Do not circular-depend analytics.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
