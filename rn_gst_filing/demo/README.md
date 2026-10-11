# Demo data for Armora GST Filing

Automated demo XML is **not** enabled in the manifest yet (`demo: []`).

Placeholder file: `demo/gst_filing_demo.xml` (empty until Prompt 14).

## Screenshot and demo setup (fictional data only)

1. Install `l10n_in`, `rn_gst_base`, `rn_gst_filing`.
2. Create company **Armora Technologies Pvt Ltd** with a **fictional** GSTIN (valid format, not a real taxpayer).
3. Optionally create a `rn.gst.registration` for that GSTIN and link it on the filing.
4. Create customers in Tamil Nadu, Karnataka, Kerala, Maharashtra with fictional GSTINs.
5. Post invoices covering:
   - Intrastate B2B (CGST+SGST)
   - Interstate B2B (IGST)
   - B2CS and B2CL
   - Export with shipping bill fields
   - Customer credit note (CDNR)
6. Upload official GSTN Offline Tool GSTR-1 template.
7. Create filing for demo period → Load (`data_loaded`) → Validate → Generate Excel.

See `static/description/screenshots/SCREENSHOTS.md` for Apps Store capture filenames.

**Never use real customer or company confidential data in demo or screenshots.**
