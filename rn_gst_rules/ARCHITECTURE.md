# Architecture: rn_gst_rules (Odoo 20)

Production architecture boundary for **Armora GST Rules**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Effective-dated GST rule configuration and reusable pre-API validation. Not a substitute for Odoo tax or portal APIs.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| rn.gst.rule effective-dated rule registry | Filing snapshot validation (rn.gst.filing.validation) |
| Shared pre-API validation service (rn.gst.rule.validation) | Invoice quality gate |
| API audit trail (rn.gst.api.audit) with secret redaction | IRN / EWB generation |
| Rule applicability resolution by date / API version | Legal rate hardcoding |
| - | Portal submission |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| rn.gst.rule effective-dated rule registry | `rn_gst_rules` | rn_gst_einvoice, rn_gst_ewaybill, rn_gst_3b (ITC utilization rules) |
| Shared pre-API validation service (rn.gst.rule.validation) | `rn_gst_rules` | rn_gst_einvoice, rn_gst_ewaybill, rn_gst_3b (ITC utilization rules) |
| API audit trail (rn.gst.api.audit) with secret redaction | `rn_gst_rules` | rn_gst_einvoice, rn_gst_ewaybill, rn_gst_3b (ITC utilization rules) |
| Rule applicability resolution by date / API version | `rn_gst_rules` | rn_gst_einvoice, rn_gst_ewaybill, rn_gst_3b (ITC utilization rules) |
| Upstream: Base GSTIN / period helpers | External / sibling | `rn_gst_rules` |

---

## Dependency graph

```text
Document / API context
        │
        ▼
rn.gst.rule.find_applicable
        │
        ▼
rn.gst.rule.validation (pre-API)
        │
        ▼
Blocking / warning results + optional api.audit
```

**Hard depends:** `rn_gst_base`

**Soft / optional:** None (runtime detection only)

**Consumes:** Base GSTIN / period helpers

**Consumed by:** rn_gst_einvoice, rn_gst_ewaybill, rn_gst_3b (ITC utilization rules)

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

Must not share model name with filing validation. Filing uses rn.gst.filing.validation.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
