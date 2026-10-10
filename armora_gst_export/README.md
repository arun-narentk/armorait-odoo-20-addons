# Armora GST Export

Odoo **18.0** module in the Armora GST Suite.

## Purpose

Export and SEZ GST document checks for Odoo 20.

- Validate export invoice completeness (shipping bill, port, etc.)
- Support SEZ / deemed export review fields already on Indian invoices
- Highlight missing export GST information before filing

## Dependencies

- `armora_gst_base`

## Status


Prompt 2 boundary: see [ARCHITECTURE.md](ARCHITECTURE.md).
Installable scaffold. Domain models, workflows, and tests are implemented in follow-up steps.

## Notes

Builds on l10n_in export fields. Does not submit documents to customs/GSTN.

## License

LGPL-3

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com