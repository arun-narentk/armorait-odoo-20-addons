# Armora GST Invoice Validator

Odoo **18.0** pre-filing GST invoice quality gate for the Armora GST Suite.

## Purpose

Validate sales invoices, vendor bills, credit notes and debit notes **before**
they reach filing, reconciliation, E-Invoice or E-Way Bill workflows.

This module identifies problems. It does **not** change accounting values
silently, file returns, submit IRN/E-Way Bill, or call the GST Portal.

## Dependencies

- `rn_gst_base` (GSTIN / POS / money helpers, shared security, menus)
- Indian localization via transitive `l10n_in`

## Current structure

```text
rn_gst_invoice_validator/
├── models/          # Issues, validation run/line, account.move hooks
├── services/        # Rule packs (stubs; engine still in AbstractModel)
├── wizard/          # Batch validation wizard scaffold
├── views/           # Invoice, issues, runs, results, wizard, menus
├── security/        # User / Manager / Administrator + record rules
├── data/            # Sequences
├── demo/            # Optional demo (later)
├── tests/           # Automated tests
└── static/description/
```

## Existing behaviour (kept)

- `rn.gst.invoice.validator` AbstractModel engine
- `rn.gst.invoice.issue` per-move issues
- Optional post blocking via company settings
- Invoice form GST validation actions

## Scaffold added in structure step

- `rn.gst.invoice.validation` (run)
- `rn.gst.invoice.validation.line` (result)
- Batch wizard shell
- Service package stubs for rule packs
- Validation run / result menus

Full rule implementations, dashboard, demo data and Apps Store page follow
in later steps.

## Limitations

- Service packs are stubs; live checks still run through the AbstractModel
- Validation run does not yet execute the full rule engine
- No GST Portal / EDI API calls from this module

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
