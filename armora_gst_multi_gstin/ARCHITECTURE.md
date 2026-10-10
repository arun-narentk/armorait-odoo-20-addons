# Architecture: armora_gst_multi_gstin (Odoo 20)

Production architecture boundary for **Armora GST Multi-GSTIN**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Company ≠ one GSTIN. Extends armora.gst.registration usage; does not redefine the model.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Multi-GSTIN resolution helpers on moves / journals (target) | Redefining armora.gst.registration from scratch |
| Registration lifecycle enhancements | Vendor GSTIN master (partner.vat) |
| Journal / document mapping to registration | Filing engine |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Multi-GSTIN resolution helpers on moves / journals (target) | `armora_gst_multi_gstin` | Filing, dashboard, compliance modules |
| Registration lifecycle enhancements | `armora_gst_multi_gstin` | Filing, dashboard, compliance modules |
| Journal / document mapping to registration | `armora_gst_multi_gstin` | Filing, dashboard, compliance modules |
| Upstream: armora.gst.registration | External / sibling | `armora_gst_multi_gstin` |

---

## Dependency graph

```text
Company
   ├── Registration A
   ├── Registration B
   └── Registration C
        │
        ▼
Document / evaluation scoped by gst_registration_id
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `filing`, `dashboard`, `rate_manager`

**Consumes:** armora.gst.registration

**Consumed by:** Filing, dashboard, compliance modules

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

Must _inherit / extend base registration; never duplicate table.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
