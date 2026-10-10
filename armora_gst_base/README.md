# Armora GST Base

Foundation module for the Armora Indian GST ecosystem on **Odoo 20.0**.

## Purpose

`armora_gst_base` is infrastructure. Other Armora GST modules depend on it for
shared helpers, security groups, menus, and company settings.

It does **not** provide GSTR-1 filing, GSTR-3B, GSTR-2B reconciliation,
E-Invoice, E-Way Bill, or GST Portal API integration. Those belong in separate
modules.

## Odoo version

- Target: Odoo 20.0 only
- Indian localization: `l10n_in`

## Installation

1. Add the `armora` addons path to your Odoo configuration.
2. Update the apps list.
3. Install **Armora GST Base**.

Demo data (when available) is optional and loads only with `--with-demo` / demo databases.

## Dependencies

| Module | Required | Reason |
|--------|----------|--------|
| `account` | Yes | Accounting settings and monetary fields |
| `l10n_in` | Yes | Indian GST state TIN codes and localization fields |

No EDI, GSTIN-status, or Enterprise reporting modules are required.

## Models

### `armora.gst.registration`

Company-scoped GST registration (supports multiple GSTINs):

- `registration_name`, `company_id`, `gstin`
- `state_id`, `state_code`
- `legal_name`, `trade_name`
- `registration_type` (regular, composition, casual, SEZ, ISD, other)
- `active`, `effective_from`, `effective_to`, `notes`

Rules:

- GSTIN is normalized and structure/checksum validated
- State / state code must match the GSTIN prefix
- Only one **active** registration per `(company, GSTIN)`
- Multi-company record rule on `company_id`
- No chatter / no `mail` dependency

## Security

| Group | Registration access |
|-------|---------------------|
| User | Read |
| Manager | Create / write |
| Administrator | Full (including unlink) |

## Features (current)

- Shared security groups: User, Manager, Administrator
- Armora GST root application menu and GST Registrations UI
- Company settings: B2CL threshold, reconciliation tolerance
- Shared constants (severity, filing status/types, document types, rates, TIN codes)
- Pure service utilities under `services/` (deterministic, no GSTN HTTP):
  - GSTIN normalize / structure / checksum
  - State TIN normalize / membership checks
  - FY and return period helpers
  - Document number and HSN/SAC normalize
  - Decimal-safe tax rounding and tolerance compare
  - Place-of-supply classification by TIN codes
- Env-facing AbstractModel wrappers (backward compatible):
  - `armora.gst.gstin.validator`
  - `armora.gst.period`
  - `armora.gst.money`
  - `armora.gst.selection`

## Architecture

```text
armora_gst_base/
├── constants/       # Shared selections and primitive codes
├── exceptions/      # GstFormatError, GstChecksumError, ...
├── services/        # Pure utilities (preferred for new code / tests)
├── models/          # Registration + AbstractModels + company settings
├── security/        # Groups, access rights, record rules
├── views/           # UI
├── data/ / demo/    # Optional data
├── tests/           # Automated tests
└── static/description/
```

Import preference for new code:

```python
from odoo.addons.armora_gst_base.services import gstin, periods, monetary
```

Existing suite modules may keep calling `env['armora.gst.*']` helpers.

## Armora GST ecosystem

Modules that build on this foundation include:

- Armora GST Filing
- Armora GST Invoice Validator
- Armora GST 2B Reconciliation
- Armora GST 3B
- Armora GST Rules
- Armora GST E-Invoice
- Armora GST E-Way Bill
- Armora GST Dashboard

## Limitations

- One company GSTIN remains on `res.company.vat` (Odoo localization).
  `armora.gst.registration` is complementary multi-GSTIN configuration.
- No GSTR filing, E-Invoice, E-Way Bill, or GST Portal API in this module.
- Broader service-layer automated tests follow in later steps.

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
