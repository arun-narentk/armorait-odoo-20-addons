# Architecture: armora_gst_rules (Odoo 20)

Production architecture boundary for **Armora GST Rules**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Effective-dated GST rule configuration and reusable pre-API validation. Not a substitute for Odoo tax or portal APIs.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| armora.gst.rule effective-dated rule registry | Filing snapshot validation (armora.gst.filing.validation) |
| Shared pre-API validation service (armora.gst.validation) | Invoice quality gate |
| API audit trail (armora.gst.api.audit) with secret redaction | IRN / EWB generation |
| Rule applicability resolution by date / API version | Legal rate hardcoding |
| - | Portal submission |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| armora.gst.rule effective-dated rule registry | `armora_gst_rules` | armora_gst_einvoice, armora_gst_ewaybill, armora_gst_3b (ITC utilization rules) |
| Shared pre-API validation service (armora.gst.validation) | `armora_gst_rules` | armora_gst_einvoice, armora_gst_ewaybill, armora_gst_3b (ITC utilization rules) |
| API audit trail (armora.gst.api.audit) with secret redaction | `armora_gst_rules` | armora_gst_einvoice, armora_gst_ewaybill, armora_gst_3b (ITC utilization rules) |
| Rule applicability resolution by date / API version | `armora_gst_rules` | armora_gst_einvoice, armora_gst_ewaybill, armora_gst_3b (ITC utilization rules) |
| Upstream: Base GSTIN / period helpers | External / sibling | `armora_gst_rules` |

---

## Dependency graph

```text
Document / API context
        │
        ▼
armora.gst.rule.find_applicable
        │
        ▼
armora.gst.validation (pre-API)
        │
        ▼
Blocking / warning results + optional api.audit
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** None (runtime detection only)

**Consumes:** Base GSTIN / period helpers

**Consumed by:** armora_gst_einvoice, armora_gst_ewaybill, armora_gst_3b (ITC utilization rules)

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

Must not share model name with filing validation. Filing uses armora.gst.filing.validation.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
