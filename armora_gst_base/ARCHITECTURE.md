# Architecture: armora_gst_base (Odoo 20)

Production architecture boundary for **Armora GST Base**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Foundation only. Shared registration, GSTIN structure helpers, periods, money, security category, root menu. Never a filing/EDI/ITC engine.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| armora.gst.registration (company multi-GSTIN master) | GSTR filing / JSON / Offline Tool |
| Structural GSTIN validation helpers (armora.gst.gstin.validator) | E-Invoice / E-Way Bill APIs |
| FY / return-period helpers (armora.gst.period) | ITC eligibility |
| Shared money / selection / company GST settings | Portal GSTIN verification |
| Armora GST security category and root menu | Tax calculation (Odoo account.tax) |
| - | Exception business rules |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| armora.gst.registration (company multi-GSTIN master) | `armora_gst_base` | All Armora GST specialist modules |
| Structural GSTIN validation helpers (armora.gst.gstin.validator) | `armora_gst_base` | All Armora GST specialist modules |
| FY / return-period helpers (armora.gst.period) | `armora_gst_base` | All Armora GST specialist modules |
| Shared money / selection / company GST settings | `armora_gst_base` | All Armora GST specialist modules |
| Armora GST security category and root menu | `armora_gst_base` | All Armora GST specialist modules |
| Upstream: l10n_in partner/move GST fields | External / sibling | `armora_gst_base` |
| Upstream: res.company / res.partner | External / sibling | `armora_gst_base` |

---

## Dependency graph

```text
l10n_in / account
        │
        ▼
armora_gst_base
        │
        ├── registration
        ├── gstin structure
        ├── periods / money
        └── security / menus
        │
        ▼
Specialist Armora GST modules
```

**Hard depends:** `account`, `l10n_in`

**Soft / optional:** None (runtime detection only)

**Consumes:** l10n_in partner/move GST fields, res.company / res.partner

**Consumed by:** All Armora GST specialist modules

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

Company VAT remains on res.company; registration is complementary multi-GSTIN config.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
