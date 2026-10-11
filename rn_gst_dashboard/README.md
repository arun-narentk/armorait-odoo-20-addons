# Armora GST Compliance Dashboard

Odoo 20 aggregation layer for the Armora GST Suite.

## Purpose

Central management workspace for GST operations. Consumes data owned by other
Armora GST modules. Does not recalculate filing, 2B matching, invoice
validation, ITC eligibility, or EDI submissions.

## Hard dependency

- `rn_gst_base`

## Optional modules (runtime detection)

- `rn_gst_filing`
- `rn_gst_2b_reconciliation`
- `rn_gst_invoice_validator`
- `rn_gst_itc` (when implemented)
- `rn_gst_einvoice` / `rn_gst_einvoice_monitor`
- `rn_gst_ewaybill` / `rn_gst_ewaybill_manager`
- `rn_gst_exception` (when implemented)
- `rn_gst_3b`, `rn_gst_audit`, `rn_gst_calendar`, …

Missing optional modules hide their sections; they do not block install.

## Structure

| Area | Status |
|------|--------|
| Filter / workspace model | Done (Step 4 KPIs) |
| Provider services | Aggregation from installed modules |
| Snapshot / filter presets | Skeleton |
| KPI UI cards / charts / action center | Later steps |
| Demo / Apps Store screenshots | Later steps |

## Security

- Dashboard User
- Dashboard Manager
- Dashboard Administrator

Source-module ACLs and multi-company rules still apply on drill-down.

## Author

ARMORA IT Technologies  
https://www.armorait.com/  
info@armorait.com
