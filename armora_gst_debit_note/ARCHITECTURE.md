# Architecture: armora_gst_debit_note (Odoo 20)

Production architecture for Armora GST debit-note compliance and control.

Target: **Odoo 20.0** Indian GST. Confirmed source only (see Prompt 1).

---

## Core principle

```text
Odoo account.move + account_debit_note  =  accounting source of truth
armora_gst_debit_note                    =  GST compliance / review layer
```

Do **not** replace `account.move`. Do **not** clone `armora_gst_credit_note` and rename fields.

---

## Debit vs credit (must stay separate)

| | Credit note | Debit note |
|--|-------------|------------|
| Detection | `move_type` in `out_refund` / `in_refund` | **`debit_origin_id` set** (usually `out_invoice` / `in_invoice`) |
| Original link | `reversed_entry_id` | **`debit_origin_id`** |
| EDI Typ | `CRN` | **`DBN`** |
| Liability | Decrease | **Increase** |
| Validation pack | Reduction / remaining credit | **Additional taxable value / tax** |

Shared low-level helpers (money, GSTIN, POS) live in `armora_gst_base`. Shared HSN/rate/exception services are consumed. Business rule packs stay separate.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| GST debit-note classification / detection | `account.move` document |
| Debit-note reason master | Accounting posting |
| Original linkage validation (`debit_origin_id`) | Tax calculation |
| Additional value/tax consistency checks | Invoice totals |
| Soft HSN / rate consumption | E-Invoice / EWB API |
| Duplicate / period checks | GSTR filing engine |
| E-Invoice applicability (DBN vs commercial) | HSN / rate masters |
| Filing readiness export | ITC |
| Exceptions / audit / CN-style review UX | Credit-note reduction rules |

---

## Responsibility matrix

| Component | Owns | Consumes |
|-----------|------|----------|
| Odoo Accounting / `account_debit_note` | Move, taxes, posting, `debit_origin_id` | — |
| `armora_gst_base` | Registrations, money, shared constants | `l10n_in` |
| `armora_gst_hsn_validator` | HSN/SAC validation | Product/line codes |
| `armora_gst_rate_manager` | Rate config / lookup | `account.tax` |
| `armora_gst_invoice_validator` | Broad invoice gate | DN readiness later |
| `armora_gst_credit_note` | CN reduction compliance | Shared helpers only |
| **`armora_gst_debit_note`** | DN increase compliance | Move + soft HSN/rate/exception/EDI |
| `armora_gst_einvoice_monitor` | IRN lifecycle display | Odoo EDI |
| `armora_gst_filing` | Returns / Offline Tool | DN document payload |
| `armora_gst_exception` | Central inbox | DN findings |
| `armora_gst_dashboard` | Suite KPIs | DN metrics |

---

## Dependency diagram

```text
account_debit_note / l10n_in
        │
        ▼
armora_gst_base
        │
        ├────────────────────────────────┐
        ▼                                ▼
armora_gst_debit_note              armora_gst_exception (soft)
        │
        │ soft consume
        ▼
armora_gst_hsn_validator / armora_gst_rate_manager
        │
        │ reverse soft: invoice validator / filing / dashboard
        ▼
armora_gst_einvoice_monitor / armora_gst_filing
```

**Hard depends:** `armora_gst_base`, `account_debit_note`  
**Not a dependency:** `armora_gst_credit_note` (sibling, not parent)

---

## Conceptual flow

```text
account.move (debit_origin_id set)
        │
        ▼
Armora GST Debit Note Layer
        │
┌───────┼───────────────┐
▼       ▼               ▼
Origin  Reason      GST Validation
        │               │
        │     ┌─────────┼─────────┐
        │     ▼         ▼         ▼
        │   HSN       Rate    Additional
        │  (soft)    (soft)   value/tax
        └─────────────┬───────────┘
                      ▼
              Duplicate / Period
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
        EDI/DBN    Filing     Exception
        (soft)    readiness   (soft)
```

Additional liability path:

```text
Original taxable value
        ↓
Additional taxable value
        ↓
Additional GST (Odoo tax results)
        ↓
Debit note validation
```

---

## Detection rules (confirmed)

A GST debit note candidate:

```text
bool(move.debit_origin_id)
```

Typical customer DN: `move_type == 'out_invoice' and debit_origin_id`  
Vendor DN: `move_type == 'in_invoice' and debit_origin_id` (filing classifier today only flags customer; this module must not ignore vendor)

Commercial debit note without GST: invoice-type move with taxes empty / non-GST treatment → e-invoice **not applicable**; do not force DBN IRP claims.

---

## Layers (future prompts)

1. Compliance fields on `account.move` (Prompt 4)  
2. Reason engine (Prompt 5)  
3. Origin / amount / HSN / rate / period / duplicate services  
4. Review wizard + reporting + security  
5. Soft EDI / filing / exception bridges  

---

## Skeleton status (Prompt 3)

Installable shells: reason, validation result, review wizard, services, security, menus.  
No parallel accounting model. Domain engines land in Prompt 4+.
