# Architecture: armora_gst_vendor_compliance (Odoo 20)

Production architecture boundary for **Armora GST Vendor Compliance**.

Target: **Odoo 20.0** Indian GST. Confirmed against repository Prompt 1 inspections. Prompt 2 locks scope only (no engine implementation in this file).

---

## Core principle

Supplier GST compliance profile / risk / findings. Not purchase recon, ITC, or GSTIN API.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Vendor compliance profile (company + partner + our GST registration) | GSTIN verification engine |
| Rules / findings / events / scores (target) | 2B / purchase matching |
| Procurement decision service (Allow/Warn/Approve/Block) | ITC calculation |
| Supplier-level signal aggregation | E-invoice API |
| - | Filing engine |

---

## Responsibility matrix

| Feature / concern | Owner | Consumer modules |
|-------------------|-------|------------------|
| Vendor compliance profile (company + partner + our GST registration) | `armora_gst_vendor_compliance` | Purchase UX, dashboard, audit |
| Rules / findings / events / scores (target) | `armora_gst_vendor_compliance` | Purchase UX, dashboard, audit |
| Procurement decision service (Allow/Warn/Approve/Block) | `armora_gst_vendor_compliance` | Purchase UX, dashboard, audit |
| Supplier-level signal aggregation | `armora_gst_vendor_compliance` | Purchase UX, dashboard, audit |
| Upstream: Verification / recon / ITC risk / IRN signals | External / sibling | `armora_gst_vendor_compliance` |

---

## Dependency graph

```text
Vendor + our GSTIN context
        │
        ▼
Soft signals → rules → findings / score
        │
        ▼
Procurement decision + exceptions
```

**Hard depends:** `armora_gst_base`

**Soft / optional:** `verification`, `2b`, `purchase_recon`, `itc`, `einvoice`, `filing`, `exception`, `multi_gstin`, `dashboard`

**Consumes:** Verification / recon / ITC risk / IRN signals

**Consumed by:** Purchase UX, dashboard, audit

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

Unknown portal data ≠ Non-Compliant. Scope by company + vendor + our registration.

---

## Prompt sequence

1. Prompt 1 – source inspection (done / assumed)
2. **Prompt 2 – this boundary lock**
3. Prompt 3+ – domain models / services / UI / tests per module pack

Do not implement Prompt 3+ engines until this boundary is accepted for the module.
