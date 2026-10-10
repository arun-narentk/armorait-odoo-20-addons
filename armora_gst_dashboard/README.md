# Armora GST Compliance Dashboard

Odoo 20 aggregation layer for the Armora GST Suite.

## Purpose

Central management workspace for GST operations. Consumes data owned by other
Armora GST modules. Does not recalculate filing, 2B matching, invoice
validation, ITC eligibility, or EDI submissions.

## Hard dependency

- `armora_gst_base`

## Optional modules (runtime detection)

- `armora_gst_filing`
- `armora_gst_2b_reconciliation`
- `armora_gst_invoice_validator`
- `armora_gst_itc` (when implemented)
- `armora_gst_einvoice` / `armora_gst_einvoice_monitor`
- `armora_gst_ewaybill` / `armora_gst_ewaybill_manager`
- `armora_gst_exception` (when implemented)
- `armora_gst_3b`, `armora_gst_audit`, `armora_gst_calendar`, …

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
