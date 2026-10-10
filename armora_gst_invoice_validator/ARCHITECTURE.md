# Architecture: armora_gst_invoice_validator (Odoo 20)

Production architecture boundary for **Armora GST Invoice Validator**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Pre-post / pre-filing invoice quality gate. Detects issues; does not file or calculate tax.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Invoice validation runs / lines / issues | HSN master engine (consumes soft) |
| Blocking vs warning severity for posting gate | Rate determination |
| Company block-post configuration | GSTIN portal verification |
| Move validation status / score fields | Filing snapshot validation |
| - | Compliance lifecycle orchestration (invoice_compliance) |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Invoice validation runs / lines / issues | `armora_gst_invoice_validator` | invoice_compliance, dashboard, customer/vendor compliance |
| Blocking vs warning severity for posting gate | `armora_gst_invoice_validator` | invoice_compliance, dashboard, customer/vendor compliance |
| Company block-post configuration | `armora_gst_invoice_validator` | invoice_compliance, dashboard, customer/vendor compliance |
| Move validation status / score fields | `armora_gst_invoice_validator` | invoice_compliance, dashboard, customer/vendor compliance |
| Upstream: account.move / l10n_in | External / sibling | `armora_gst_invoice_validator` |
| Upstream: Base GSTIN / POS helpers | External / sibling | `armora_gst_invoice_validator` |

---

## Dependency graph

```text
Draft / post invoice
        │
        ▼
Validator checks (GSTIN, POS, tax, HSN soft, export, EDI prerequisites)
        │
        ▼
Issues + score → optional block post
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `armora_gst_hsn_validator`, `armora_gst_rate_manager`, `armora_gst_in_verification`, `armora_gst_exception`

**Consumes:** account.move / l10n_in, Base GSTIN / POS helpers

**Consumed by:** invoice_compliance, dashboard, customer/vendor compliance

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

Separate from armora_gst_invoice_compliance (orchestration / readiness).

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
