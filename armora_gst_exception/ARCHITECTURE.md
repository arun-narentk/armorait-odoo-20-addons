# Architecture: armora_gst_exception (Odoo 20)

Production architecture boundary for **Armora GST Exception Center**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Central exception lifecycle inbox. No GST business rules inside.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Exception records / assignment / resolution lifecycle (target) | Detection engines (validator, 2B, HSN, …) |
| Severity / status framework | Auto-fix of source documents |
| Idempotent exception posting API for specialists | Python GstError in base (different concern) |
| - | Invoice-local armora.gst.invoice.issue |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Exception records / assignment / resolution lifecycle (target) | `armora_gst_exception` | All specialists (soft post), dashboard, audit |
| Severity / status framework | `armora_gst_exception` | All specialists (soft post), dashboard, audit |
| Idempotent exception posting API for specialists | `armora_gst_exception` | All specialists (soft post), dashboard, audit |
| Upstream: Structured posts from specialists | External / sibling | `armora_gst_exception` |

---

## Dependency graph

```text
Specialist finding
        │
        ▼
ExceptionService.post (idempotent)
        │
        ▼
Inbox → assign → resolve / reopen
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** None (runtime detection only)

**Consumes:** Structured posts from specialists

**Consumed by:** All specialists (soft post), dashboard, audit

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

Foundation must not hard-depend specialists. Soft bridges only.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
