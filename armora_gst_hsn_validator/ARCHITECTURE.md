# Architecture: armora_gst_hsn_validator (Odoo 20)

Production architecture for the Armora GST HSN/SAC validation and control layer.

Target: **Odoo 20.0** Indian GST. Confirmed source fields only (see Prompt 1 inspection).

---

## Principles

1. Do not duplicate Odoo `l10n_in` HSN/SAC storage or tax computation.
2. Reuse `product.template.l10n_in_hsn_code`, `account.move.line.l10n_in_hsn_code`,
   `res.company.l10n_in_hsn_code_digit`.
3. Reuse `armora_gst_base.services.documents` (`normalize_hsn_sac`, `validate_hsn_sac`).
4. This module **owns** HSN/SAC-specific validation, history, bulk and rules.
5. `armora_gst_invoice_validator` **consumes** results (soft); it must not be a hard dependency.
6. `armora_gst_exception` receives mapped issues when installed (soft).
7. Multi-company isolation on all result / run models.
8. Multi-GSTIN: use `armora.gst.registration` as optional context; digit policy remains
   company-level (`l10n_in_hsn_code_digit`) until Odoo exposes per-registration digits.
9. No unrestricted `sudo()`. Prefetch for batch paths. No giant static HSN master DB.
10. Separate **format validation** from **authoritative verification**.

---

## Ownership map

| Owns | Does not own | Consumes | Consumed by |
|------|--------------|----------|-------------|
| HSN/SAC format + consistency engine | Tax rates / CGST bands | `l10n_in_hsn_code` fields | Invoice validator |
| Validation results + history | Invoice quality gate | Base HSN helpers | Filing (cleaner data) |
| Rule registry + severity | EDI / EWB submit | Company digit policy | Exception center |
| Product / bulk UX for HSN | Partner GSTIN verify | Registrations (context) | Dashboard KPIs |
| Optional provider abstraction | Government HSN master (unless provider) | Product type for heuristics | |

---

## Dependency diagram

```text
l10n_in
   │
   ▼
armora_gst_base
   │
   ├────────────────────────────┐
   ▼                            ▼
armora_gst_hsn_validator    armora_gst_exception (soft)
   │
   │  (soft / reverse: invoice validator calls HSN API)
   ▼
armora_gst_invoice_validator
   │
   ▼
armora_gst_dashboard / armora_gst_filing
```

**Hard depends:** `armora_gst_base` only.

**Soft / later:** `armora_gst_exception`, hook from `armora_gst_invoice_validator`.

---

## Conceptual flow

```text
Product / Invoice / Transaction
        ↓
HSN/SAC Extraction  (l10n_in_hsn_code only; no invented SAC field)
        ↓
HSN/SAC Validation Engine
   ┌────────────┼────────────┐
   ▼            ▼            ▼
Format     Consistency    Provider
(Level 1)   (Level 2)    (Level 3; default unavailable)
   └────────────┼────────────┘
                ▼
        Validation Results
                ↓
        Severity Classification
                ↓
        Exception Framework (optional)
                ↓
        Reports / Action Center
```

### Verification discipline

| Level | Meaning |
|-------|---------|
| Format valid | 4/6/8 digits + company min length |
| Classification complete | Code present where policy requires |
| Internally consistent | Line vs product; optional goods/service heuristic |
| Externally verified | Only if a configured provider confirms |

`format_valid=True` does **not** imply government approval.

---

## Layers

### 1. Data layer

| Model | Role |
|-------|------|
| `armora.gst.hsn.validation.result` | One finding (product / move line / code) |
| `armora.gst.hsn.validation.run` | Batch or scheduled run header |
| `armora.gst.hsn.validation.rule` | Rule metadata (code, severity, active) |
| `armora.gst.hsn.validation.wizard` | Transient bulk UI |

Reuse Odoo fields; do not add a second product HSN Char.

Optional related UX fields on `product.template` / `account.move` only for
status shortcuts (Prompt 7/8), never replacing `l10n_in_hsn_code`.

### 2. Validation engine

Service-oriented (not create/write-only logic):

- Input: product, move line, move, explicit code, company context
- Output: structured dicts / result records
- Prefetch for batches

### 3. Rule layer

Registry-driven rules (`HSN_MISSING`, `HSN_INVALID_FORMAT`, …) evaluated
deterministically. Configurable severity where useful. Independently testable.

### 4. Service layer

| Service | Responsibility |
|---------|----------------|
| `hsn_format_validator` | Structure / length / characters (wraps base) |
| `hsn_consistency_validator` | Product↔line, digit policy, type heuristics |
| `hsn_validation_service` | Orchestration + persist results |
| `hsn_provider` | Authoritative provider interface (default: unavailable) |
| `hsn_exception_bridge` | Soft post to `armora_gst_exception` |

### 5. Exception integration

Map rule codes → exception categories when exception module is installed.
Idempotent; module remains usable without it.

### 6. Product integration

Non-destructive validate actions; status / history navigation.
Never auto-rewrite `l10n_in_hsn_code`.

### 7. Invoice integration

Reusable API for invoice validator. Prefer warn/error records over post-blocking
unless company config explicitly enables blocking.

### 8. Batch validation

Wizard + optional cron: products / invoices / bills; batched; idempotent;
record-rule safe.

### 9. Reporting

`read_group` metrics from results (missing / invalid / warning / unresolved).
No fake KPIs; dashboard consumes later.

### 10. Security

| Group | Rights |
|-------|--------|
| User | View results, run permitted validation |
| Manager | Bulk, resolve, broader reports, config |
| Administrator | Rules, technical settings, schedules |

Company record rules on result / run. No credential storage.

### 11. Configuration

Company-scoped: enable validation, scopes (product / invoice / bill),
severity defaults, optional blocking, cron batch size.
Global only if truly technical (rare).

### 12. Tests

Format vs consistency vs provider-unavailable; product / invoice / bulk /
security / multi-company / idempotency. Never assert fabricated government verify.

---

## Confirmed Odoo fields (do not invent replacements)

- `product.template.l10n_in_hsn_code`
- `product.template.l10n_in_hsn_warning` (Odoo UI; leave intact)
- `account.move.line.l10n_in_hsn_code`
- `res.company.l10n_in_hsn_code_digit`
- Move warnings via `l10n_in_warning` key `invalid_hsn_code_length`

No separate SAC Char in Odoo 20 `l10n_in` in this tree.

---

## Skeleton status (Prompt 3)

File tree and empty/stub models/services/views are installable.
Domain fields, engine, and rules land in Prompts 4+.
