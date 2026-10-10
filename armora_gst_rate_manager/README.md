# Armora GST Rate Manager

Odoo **18.0** module in the Armora GST Suite.

## Purpose

GST rate configuration and change control for Odoo 20.

- Logical rate master (shell) with future effective dating
- Mapping to existing `account.tax` (not a second tax engine)
- Conflict / change / history shells
- Controlled bulk update wizard shell

See [ARCHITECTURE.md](ARCHITECTURE.md) for ownership and dependency rules.

## Dependencies

- `armora_gst_base` (brings `account` + `l10n_in`)

Optional later (soft): `armora_gst_hsn_validator`, `armora_gst_exception`.
Invoice validator may consume rate lookup; this module does **not** depend on it.

## Status

Installable (`18.0.1.2.0`). GST rate master fields, effective dating and historical write protection are implemented. Change workflow and mapping validation land in follow-up prompts.

## Important

Odoo `account.tax` remains responsible for tax calculation. Draft rate changes must not alter live taxes until an explicit controlled apply is implemented.

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
