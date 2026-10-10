# Architecture: armora_gst_in_verification (Odoo 20)

Production architecture boundary for **Armora GSTIN Verification**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

External / portal verification evidence owner. Structure ≠ verified.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Verification requests / responses / history (target) | Structural-only checks (base validator) |
| Verification status timestamps and source | Customer/vendor compliance scoring |
| Partner / company GSTIN verification workflows | Fabricated portal responses |
| - | Invoice validation gate |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Verification requests / responses / history (target) | `armora_gst_in_verification` | Customer / vendor compliance, invoice validator soft |
| Verification status timestamps and source | `armora_gst_in_verification` | Customer / vendor compliance, invoice validator soft |
| Partner / company GSTIN verification workflows | `armora_gst_in_verification` | Customer / vendor compliance, invoice validator soft |
| Upstream: Base GSTIN normalize/validate | External / sibling | `armora_gst_in_verification` |
| Upstream: optional portal provider | External / sibling | `armora_gst_in_verification` |

---

## Dependency graph

```text
GSTIN
        │
        ▼
Structure check (base) → external verify (this module)
        │
        ▼
Evidence store → consumers interpret status
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `l10n_in_gstin_status`, `customer/vendor compliance`, `exception`

**Consumes:** Base GSTIN normalize/validate, optional portal provider

**Consumed by:** Customer / vendor compliance, invoice validator soft

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

Unavailable provider → Verification Unavailable, not Verified.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
