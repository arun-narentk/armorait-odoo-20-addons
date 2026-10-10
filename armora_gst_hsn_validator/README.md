# Armora GST HSN/SAC Validator

Odoo **18.0** module in the Armora GST Suite.

## Purpose

Validate HSN/SAC classification data on products and GST documents.

- Reuse Odoo `l10n_in_hsn_code` (do not invent a second HSN field)
- Format and length checks via `armora_gst_base` helpers
- Validation results, runs and rule registry (shells in this version)
- Clear split: format valid is not government verified

See [ARCHITECTURE.md](ARCHITECTURE.md) for ownership, layers and dependency rules.

## Dependencies

- `armora_gst_base` (brings `account` + `l10n_in`)

Optional later (soft): `armora_gst_exception`. Invoice validator may consume this module; this module does **not** depend on the invoice validator.

## Status

Installable skeleton (`18.0.1.1.0`). Validation engine, domain fields and product/invoice UX land in follow-up prompts.

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
