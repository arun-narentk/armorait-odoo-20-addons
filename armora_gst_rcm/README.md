# Armora GST Reverse Charge

Odoo 20.0 module in the Armora GST Suite.

## What it does

- RCM rules for notified supplies (section 9(3)), supplies from unregistered persons (section 9(4)) and import of services. Each rule is linked to products, product categories or expense accounts and to a same-state and an other-state reverse charge tax.
- Vendor bill check: a draft bill warns when a line falls under a rule but has no reverse charge tax; "Apply RCM Taxes" puts the rule's tax on it.
- Self-invoice under section 31(3)(f) for reverse charge purchases from unregistered suppliers, with its own numbering, PDF and the 30-day due date.
- Time of supply: for services, the payment date or the 61st day after the supplier invoice, whichever is earlier; for goods, the invoice date or the payment date.
- RCM register of posted reverse charge bills with tax, time-of-supply month, payment and self-invoice status.

When Armora GST GSTR-3B is installed, its "Fill from Books" warns about reverse charge bills whose tax month differs from their invoice month.

## Not covered

- The seeded rules carry no tax rates: pick the taxes and check each notification's conditions.
- Payment vouchers under section 31(3)(g) are not printed.

## Dependencies

- `armora_gst_base`

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
