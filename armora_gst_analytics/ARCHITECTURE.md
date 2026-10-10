# Architecture: armora_gst_analytics (Odoo 20)

Production architecture boundary for **Armora GST Analytics**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Historical analysis, trends, comparisons, ratios. Consumes facts; does not redefine GST business truth.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Analytical facts / dimensions / metrics (target) | ITC eligibility |
| Period comparison / trend services | 2B matching |
| Management / accountant analytical views | Filing / IRN / HSN / rate engines |
| Refresh metadata / freshness | Operational dashboard workspace |
| Cross-module KPI dictionary | Accounting balances as source of truth rewrite |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Analytical facts / dimensions / metrics (target) | `armora_gst_analytics` | Management reporting |
| Period comparison / trend services | `armora_gst_analytics` | Management reporting |
| Management / accountant analytical views | `armora_gst_analytics` | Management reporting |
| Refresh metadata / freshness | `armora_gst_analytics` | Management reporting |
| Cross-module KPI dictionary | `armora_gst_analytics` | Management reporting |
| Upstream: Authoritative module results + account.move amounts | External / sibling | `armora_gst_analytics` |

---

## Dependency graph

```text
Source modules / accounting
        │
        ▼
Facts + dimensions → metrics
        │
        ▼
Trends / comparisons / drill-down
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `filing`, `2b`, `itc`, `exception`, `validator`, `HSN`, `rate`, `einvoice`, `tds_tcs`, `dashboard`

**Consumes:** Authoritative module results + account.move amounts

**Consumed by:** Management reporting

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

Unknown data → Unknown metric, not fabricated non-compliance.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
