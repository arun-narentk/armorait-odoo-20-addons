# Architecture: armora_gst_rcm (Odoo 20)

Production architecture boundary for **Armora GST Reverse Charge**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

RCM applicability / compliance layer. Unregistered ≠ automatically RCM.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| RCM applicability rules (effective-dated) (target) | Odoo RC tax computation |
| RCM compliance findings / review | ITC auto-claim of RCM |
| RCM readiness signals | TDS/TCS engines |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| RCM applicability rules (effective-dated) (target) | `armora_gst_rcm` | ITC soft handoff, filing, dashboard |
| RCM compliance findings / review | `armora_gst_rcm` | ITC soft handoff, filing, dashboard |
| RCM readiness signals | `armora_gst_rcm` | ITC soft handoff, filing, dashboard |
| Upstream: l10n_in reverse charge taxes / fiscal positions | External / sibling | `armora_gst_rcm` |

---

## Dependency graph

```text
Supply context → RCM rule evaluate → findings
        │
        ▼
Liability signal (≠ ITC)
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `invoice_validator`, `itc`, `exception`, `filing`

**Consumes:** l10n_in reverse charge taxes / fiscal positions

**Consumed by:** ITC soft handoff, filing, dashboard

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

Sibling to TDS/TCS, not under either.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
