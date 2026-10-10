# Armora GST Debit Note

Odoo **18.0** module in the Armora GST Suite.

## Purpose

GST debit-note compliance and control for Odoo 20.

- Detect debit notes via `debit_origin_id` (not `out_refund`)
- Reason master and validation result shells
- Review wizard shell focused on **additional** taxable value / tax

See [ARCHITECTURE.md](ARCHITECTURE.md). Debit notes **increase** GST liability; credit notes decrease it. This module is not a rename of `armora_gst_credit_note`.

## Dependencies

- `armora_gst_base`
- `account_debit_note`

Optional later (soft): HSN validator, rate manager, exception center, e-invoice monitor.

## Status

Installable skeleton (`18.0.1.1.0`). Compliance fields and validation engines land in follow-up prompts.

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
