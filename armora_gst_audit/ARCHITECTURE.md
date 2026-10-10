# Architecture: armora_gst_audit (Odoo 20)

Production architecture boundary for **Armora GST Audit**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Suite control tower for audit runs / evidence packs. Orchestrates; does not re-validate.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Audit runs / findings packaging (target) | Validator / 2B / filing engines |
| Evidence references across modules | Exception lifecycle replacement |
| Period audit pack exports | Statutory audit certification claims |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Audit runs / findings packaging (target) | `armora_gst_audit` | Internal / external review workflows |
| Evidence references across modules | `armora_gst_audit` | Internal / external review workflows |
| Period audit pack exports | `armora_gst_audit` | Internal / external review workflows |
| Upstream: Specialist results via soft adapters | External / sibling | `armora_gst_audit` |

---

## Dependency graph

```text
Audit request (period / company / GSTIN)
        │
        ▼
Soft adapters collect evidence
        │
        ▼
Findings pack (no duplicate detection)
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `validator`, `2b`, `filing`, `exception`, `customer/vendor compliance`, `itc`

**Consumes:** Specialist results via soft adapters

**Consumed by:** Internal / external review workflows

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

Soft-post to exception; never replace exception center.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
