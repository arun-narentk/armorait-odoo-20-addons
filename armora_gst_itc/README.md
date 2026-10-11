# Armora GST ITC Ledger

Odoo 20.0 module in the Armora GST Suite.

## What it does

- Monthly ITC ledger: ITC availed from the month's vendor bills, by tax head.
- ITC type on each vendor bill line: eligible, blocked under section 17(5), or common credit.
- Rule 42: common credit reversed in the ratio of exempt, nil rated and non-GST turnover to total turnover of the month.
- Rule 37: a bill not fully paid 180 days after its date is reversed (unpaid share) in the month the 180 days end, with 18% interest shown; the credit is reclaimed in the month the supplier is paid.
- Electronic credit ledger: opening (last month's closing), net ITC, credit used in that month's GSTR-3B, closing.
- ITC register per bill with the amount paid by month end and the GSTR-2B status.

When Armora GST GSTR-3B is installed, its "Fill from Books" takes blocked credit and Rule 42 into 4(B)(1), Rule 37 into 4(B)(2), reclaims into 4(A)(5) and 4(D)(1), and the opening credit from the month's ledger.

## Not covered

- Rule 43 (capital goods used for exempt supplies) is not computed.
- No connection to the GST Portal or a GSP.

## Dependencies

- `armora_gst_base`
- `mail`

## License

OPL-1

## Support

- Website: https://www.armorait.com/
- Email: info@armorait.com
