# Architecture: armora_gst_tds_tcs (Odoo 20)

Production architecture boundary for **Armora GST TDS/TCS**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

GST TDS (s.51) and GST TCS (s.52) are separate engines. Not Income-tax TDS/TCS.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| GST TDS deduction compliance (target) | l10n_in_withholding Income-tax engine |
| GST TCS collection compliance (target) | Accounting payment reconciliation replacement |
| Effective-dated rate configuration (no hardcode) | ITC engine |
| Separate TDS vs TCS reporting | Hardcoded 0.5%/1% without effective dating |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| GST TDS deduction compliance (target) | `armora_gst_tds_tcs` | Analytics, filing readiness |
| GST TCS collection compliance (target) | `armora_gst_tds_tcs` | Analytics, filing readiness |
| Effective-dated rate configuration (no hardcode) | `armora_gst_tds_tcs` | Analytics, filing readiness |
| Separate TDS vs TCS reporting | `armora_gst_tds_tcs` | Analytics, filing readiness |
| Upstream: account.move / payment contexts | External / sibling | `armora_gst_tds_tcs` |

---

## Dependency graph

```text
Transaction → TDS engine | TCS engine (separate)
        │
        ▼
Configured rates by date → compliance records
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `exception`, `filing`, `dashboard`, `l10n_in_withholding coexistence`

**Consumes:** account.move / payment contexts

**Consumed by:** Analytics, filing readiness

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

TCS on net taxable supplies, not invoice total. Soft coexistence with IT withholding only.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
