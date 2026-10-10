# Architecture: armora_gst_rate_manager (Odoo 20)

Production architecture for Armora GST rate configuration and change control.

Target: **Odoo 20.0** Indian GST. Confirmed source models only (see Prompt 1).

---

## Core principle

```text
Odoo account.tax  =  tax calculation and accounting source of truth
armora_gst_rate_manager  =  rate intelligence, dating, mapping, change control
```

This module must **never** replace `compute_all` / invoice totals / journal entries.

---

## Ownership map

| Owns | Does not own |
|------|----------------|
| Logical GST rate definitions | Tax calculation |
| Effective dating / versions | Accounting entries |
| Applicability metadata | Invoice totals |
| Mapping to existing `account.tax` | ITC eligibility |
| Validation and conflict detection | GST filing / 2B |
| Change workflow + audit | HSN/SAC classification |
| Controlled bulk updates | E-Invoice / E-Way Bill APIs |
| Lookup of configured rates | Invented UTGST Odoo field (use SGST as Odoo does) |

### Consumes

- `account.tax`, `account.tax.group`, repartition tags (`l10n_in_tax_type`)
- Fiscal positions (read / validate; no silent rewrite)
- `product.template.taxes_id` / `supplier_taxes_id`
- `product.template.l10n_in_hsn_code` (association only)
- `armora_gst_base` rate Decimal helpers (`normalize_gst_rate`, `split_igst_rate_to_cgst_sgst`, `STANDARD_GST_RATES`)
- Optional: `armora_gst_hsn_validator` classification results
- Optional: `armora.gst.registration` as context

### Consumed by

- `armora_gst_invoice_validator` (rate consistency checks later)
- `armora_gst_exception` (soft)
- `armora_gst_dashboard` / analytics (metrics only)

---

## Dependency diagram

```text
l10n_in / account
        │
        ▼
armora_gst_base
        │
        ├────────────────────────────┐
        ▼                            ▼
armora_gst_rate_manager          armora_gst_exception (soft)
        │
        │  soft consume (optional)
        ▼
armora_gst_hsn_validator
        │
        │  reverse soft: invoice validator calls rate lookup
        ▼
armora_gst_invoice_validator / dashboard
```

**Hard depends:** `armora_gst_base` only.

**No circular deps:** HSN validator must not depend on rate manager; invoice validator must not be a hard dependency of rate manager.

---

## Conceptual flow

```text
                 GST RATE MANAGER
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   RATE MASTER    RATE VERSION    APPLICABILITY
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                EFFECTIVE DATE
                       ▼
                 RATE VALIDATOR
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      HSN/SAC      Odoo Tax       Conflict
     association    mapping       detection
          │            │            │
          └────────────┼────────────┘
                       ▼
                IMPACT ANALYSIS
                       ▼
                 APPROVAL FLOW
                       ▼
                 CONTROLLED UPDATE
                       ▼
                  AUDIT TRAIL
                       ▼
                  account.tax
```

Indian chart pattern to respect:

- Intra-state: group tax (e.g. `sgst_sale_18` = SGST + CGST children)
- Inter-state: `igst_sale_18`
- Cess: separate taxes where used
- `l10n_in_tax_type`: computed from tags (`igst`/`cgst`/`sgst`/`cess`)

---

## Layers

### 1. GST rate master

Logical rate definition (band / label / components as metadata). Links to Odoo taxes; does not duplicate computation.

### 2. Rate version / history

Append-only versions with `effective_from` / `effective_to`. Never overwrite a historical version in place when a new rate becomes effective.

### 3. Effective-date engine

`get_rate_for_date`, overlap detection, active/expired/future classification.

### 4. HSN/SAC mapping

Optional applicability to codes. Classification validation stays in `armora_gst_hsn_validator`.

### 5. Odoo tax mapping

M2O / M2M to existing `account.tax` (sale group, purchase group, IGST sale/purchase, cess). Read-only validation by default; writes only via controlled update.

### 6. Rate validation

Structured results (rule code, severity, message). Reuse Decimal helpers from base.

### 7. Conflict detection

Overlaps, mapping %, inactive taxes, company mismatch, missing maps.

### 8. Change management

Draft → review/approved → scheduled → effective → archived (only states that add value). Draft never alters live taxes.

### 9. Bulk update

Preview → confirm → apply; transactional; auditable; idempotent.

### 10. Reporting

Current / upcoming / expired / conflicts / mismatches. Metrics for dashboard; no fake KPIs.

### 11. Security

User / Manager / Administrator. Company record rules. No unrestricted `sudo()`. Live tax mutation requires elevated rights + explicit apply.

### 12. Integration services

| Service | Role |
|---------|------|
| Lookup | Configured rate for date / company / applicability |
| Mapping | Validate linked `account.tax` |
| Conflict | Structured conflict records |
| Validation | Component and mapping checks |
| Activation | Scheduled apply (idempotent) |
| Exception bridge | Soft post to exception center |

Lookup returns configuration only, never invoice tax amounts.

---

## Confirmed Odoo fields (do not invent replacements)

- `account.tax.amount`, `amount_type`, `type_tax_use`, `children_tax_ids`, `tax_group_id`, `active`, `company_id`
- `account.tax.l10n_in_tax_type`, `l10n_in_reverse_charge`
- `account.tax.group` (sgst/cgst/igst/cess/gst/…)
- `account.tax.repartition.line` + `account.account.tag`
- `product.template.taxes_id`, `supplier_taxes_id`, `l10n_in_hsn_code`
- `account.fiscal.position.map_tax`

---

## Skeleton status (Prompt 3)

Installable shells for rate / change / history / conflict models, services, wizard, security and menus.
Domain fields, versioning engine and workflows land in Prompts 4+.
