# Architecture: armora_gst_credit_note (Odoo 20)

Production architecture boundary for **Armora GST Credit Note**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Credit-note reduction compliance layer. Sibling to debit note; not a clone rename.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| CN GST compliance validation / reasons (target) | account.move refund posting |
| Reduction / remaining credit checks | Debit-note increase rules |
| CN review UX | Tax calculation |
| - | EDI submit |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| CN GST compliance validation / reasons (target) | `armora_gst_credit_note` | Filing, dashboard, invoice compliance |
| Reduction / remaining credit checks | `armora_gst_credit_note` | Filing, dashboard, invoice compliance |
| CN review UX | `armora_gst_credit_note` | Filing, dashboard, invoice compliance |
| Upstream: out_refund / in_refund | External / sibling | `armora_gst_credit_note` |
| Upstream: reversed_entry_id | External / sibling | `armora_gst_credit_note` |

---

## Dependency graph

```text
Refund move → CN compliance checks → readiness / exceptions
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `HSN`, `rate`, `exception`, `einvoice`, `filing`, `invoice_validator`

**Consumes:** out_refund / in_refund, reversed_entry_id

**Consumed by:** Filing, dashboard, invoice compliance

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

Detection via move_type refund; DN uses debit_origin_id.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
