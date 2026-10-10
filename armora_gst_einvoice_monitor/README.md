# Armora GST E-Invoice Monitor

Odoo **18.0** module in the Armora GST Suite.

## Purpose

Monitor e-Invoice IRN status and exceptions for Odoo 20.

- Track IRN generation status on Indian GST invoices
- Surface pending, failed, and cancelled e-Invoice cases
- Provide accountant views without replacing Odoo EDI engines

## Dependencies

- `armora_gst_base`

## Status


Prompt 2 boundary: see [ARCHITECTURE.md](ARCHITECTURE.md).
Installable scaffold. Domain models, workflows, and tests are implemented in follow-up steps.

## Notes

Complements Odoo l10n_in_edi and existing armora_gst_einvoice extensions.

## License

LGPL-3

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com